import streamlit as st
import asyncio
import uuid
import threading
import time
from datetime import datetime

from model.open_ai_agent import stream_openai_response
from tools.auto_trader.auto_trader import AutoTrader

def show_sidebar():
    st.title("암호화폐 거래 AI Agent")
    chat_tab, chat_settings_tab, auto_trader_tab = st.tabs(["채팅", "Agent 설정", "자동 거래"])

    # 세션 상태에 Agent 상태 변수 초기화
    if 'agent_run_count' not in st.session_state:
        st.session_state.agent_run_count = 0
    
    if 'agent_start_time' not in st.session_state:
        st.session_state.agent_start_time = None

    # 세션 상태 초기화 부분에 conversation_id 추가
    if 'conversation_id' not in st.session_state:
        st.session_state.conversation_id = f"conversation_{uuid.uuid4()}"
        
    # 자동 거래 에이전트 초기화
    if 'auto_trader' not in st.session_state:
        st.session_state.auto_trader = None
    
    if 'auto_trader_settings' not in st.session_state:
        st.session_state.auto_trader_settings = {
            'interval_minutes': 5,
            'max_investment': 100000,
            'max_trading_count': 3,
            'target_coins': ["BTC", "ETH", "XRP", "SOL", "ADA"],
            'risk_level': "중립적",
            'model_options': "gpt-4o-mini"
        }

    # Agent 실행 시간 계산 함수
    def calculate_runtime():
        if st.session_state.agent_start_time:
            current_time = datetime.now()
            runtime = current_time - st.session_state.agent_start_time
            minutes = int(runtime.total_seconds() // 60)
            return f"{minutes}분"
        return "0분"

    with chat_tab:
        chat_container = st.container(height=650, border=True)
        
        # 사용자 입력 처리 (채팅 컨테이너 아래에 배치)
        user_prompt = st.chat_input(
            placeholder="어떻게 투자할까요?",
            accept_file=True,
            file_type=None
        )

        # 채팅 기록 채우기 
        with chat_container:
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.write(message["content"])
        
            if user_prompt:
                st.session_state.agent_run_count += 1
                user_prompt_text = user_prompt.text if user_prompt.text else ""
                st.session_state.messages.append({"role": "user", "content": user_prompt_text})
                
                # 스트리밍 방식으로 응답 생성 및 표시
                with chat_container:
                    with st.chat_message("user"):
                        st.write(user_prompt_text)
                        
                    with st.chat_message("assistant"):
                        response_placeholder = st.empty()
                        # 스트리밍 응답 처리
                        # 이벤트 루프 생성 및 관리 방식 변경
                        full_response = ""
                        sent_data = f"입력: {user_prompt_text[:50]}..., 모델: {st.session_state.model_options}"
                        print(f"요청 데이터: {sent_data}")

                        try:
                            # 기존 이벤트 루프 가져오기 시도
                            try:
                                loop = asyncio.get_event_loop()
                            except RuntimeError:
                                # 이벤트 루프가 없으면 새로 생성
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                            
                            # 비동기 코루틴 함수
                            async def process_chunks():
                                nonlocal full_response
                                full_response = ""
                                try:
                                    async for chunk in stream_openai_response(
                                        user_prompt_text,
                                        st.session_state.model_options,
                                        st.session_state.conversation_id
                                    ):
                                        print(f"청크 수신: {len(chunk)} 바이트")
                                        full_response += chunk
                                        response_placeholder.markdown(full_response + "▌")
                                    
                                    response_placeholder.markdown(full_response)
                                    return full_response
                                except Exception as e:
                                    error_msg = f"응답 생성 중 오류: {str(e)}"
                                    print(error_msg)
                                    response_placeholder.markdown(error_msg)
                                    return error_msg
                            
                            # 기존 루프에서 실행하거나 새 루프에서 실행
                            if loop.is_running():
                                print("기존 이벤트 루프 사용 중")
                                task = asyncio.create_task(process_chunks())
                                full_response = st.session_state.get("_temp_response", "")
                                st.session_state["_temp_task"] = task
                            else:
                                print("새 이벤트 루프 실행")
                                full_response = loop.run_until_complete(
                                    asyncio.wait_for(process_chunks(), timeout=60)
                                )
                            
                            print(f"응답 완료: {len(full_response)} 자")
                            
                        except asyncio.TimeoutError:
                            full_response = "응답 생성 시간이 초과되었습니다. 다시 시도해주세요."
                            response_placeholder.markdown(full_response)
                            print("타임아웃 발생")
                        except Exception as e:
                            full_response = f"오류 발생: {str(e)}"
                            response_placeholder.markdown(full_response)
                            print(f"예외 발생: {str(e)}")

                        # 응답 기록에 저장
                        st.session_state.messages.append({"role": "assistant", "content": full_response})

    with chat_settings_tab:
        with st.expander("Agent 상태", expanded=True):
            agent_status_col1, agent_status_col2 = st.columns(2)
            with agent_status_col1:
                st.markdown(
                f"""
                    Agent 작동 횟수 :primary-background[**{st.session_state.agent_run_count}회**]
                    
                """
                )
            with agent_status_col2:
                st.markdown(
                f"""
                    Agent 작동 시간 :primary-background[**{calculate_runtime()}**]
                """
                )

        with st.expander("Agent 설정", expanded=True):
            reboot_button = st.button("Agent 재부팅", use_container_width=True)
            # 수동 재부팅 버튼 처리
            if reboot_button:
                st.session_state.agent_run_count = 0
                st.session_state.messages = [{"role": "assistant", "content": "안녕하세요! 투자에 관해 무엇을 도와드릴까요?"}]
                st.session_state.agent_start_time = datetime.now()
                # 대화 ID 초기화
                st.session_state.conversation_id = f"conversation_{uuid.uuid4()}"
                st.success("Agent가 재부팅되었습니다.")
                st.rerun()
            reboot_frequency = st.text_input("Agent 재부팅 주기 (작동 횟수)", value="10")

            # 재부팅 주기 체크 및 LLM 초기화
            try:
                reboot_freq = int(reboot_frequency)
                if st.session_state.agent_run_count >= reboot_freq:
                    st.session_state.agent_run_count = 0  # 카운터 초기화
                    st.session_state.messages = [{"role": "assistant", "content": "안녕하세요! 투자에 관해 무엇을 도와드릴까요?"}]  # 채팅 기록 초기화
                    st.session_state.agent_start_time = datetime.now()  # 시작 시간 재설정
                    st.success(f"Agent가 {reboot_freq}회 작동 후 자동으로 재부팅되었습니다.")
                    st.rerun()
            except ValueError:
                st.error("재부팅 주기는 숫자로 입력해주세요.")

            st.session_state.model_options = st.selectbox("LLM 모델 선택", ("gpt 4o", "gpt 4o mini"))


        with st.expander("사용자 요구사항", expanded=True):
            user_requirement = st.text_area("사용자 맞춤 지시", value="비트코인을 주로 투자하고 싶어")
            st.session_state['user_requirement'] = user_requirement

            # 위험 성향 선택 시 세션 상태에 저장
            risk_style = st.select_slider(
                "위험 성향",
                options=["보수적", "중립적", "공격적"],
                value="중립적",
                key="sidebar_risk_style"
            )
            st.session_state['risk_style'] = risk_style

        # 설정 적용 버튼
        if st.button("설정 적용하기", use_container_width=True, type="primary", key="apply_settings"):
            st.success("설정이 적용되었습니다.")
            
    with auto_trader_tab:
        # 자동 거래 설정
        st.header("자동 거래 설정")
        
        # 작동 주기 설정
        auto_trader_col1, auto_trader_col2, auto_trader_col3 = st.columns(3)
        
        with auto_trader_col1:
            interval_minutes = st.text_input(
                "분석 간격 (분)", 
                value=str(st.session_state.auto_trader_settings['interval_minutes']),
                key="interval_minutes_setting"
            )
            
        with auto_trader_col2:
            max_trading_count = st.text_input(
                "일일 최대 거래 횟수", 
                value=str(st.session_state.auto_trader_settings['max_trading_count']),
                key="max_trading_count_setting"
            )
            
        with auto_trader_col3:
            max_investment = st.text_input(
                "최대 투자 금액 (원)", 
                value=str(st.session_state.auto_trader_settings['max_investment']),
                key="max_investment_setting"
            )
        
        # 자동 거래 시작/중지 버튼
        auto_trader_control_col1, auto_trader_control_col2 = st.columns(2)
        
        with auto_trader_control_col1:
            if st.button("자동 거래 시작", key="start_auto_trader", use_container_width=True, 
                        disabled=(st.session_state.auto_trader is not None and st.session_state.auto_trader.is_running)):
                try:
                    interval_minutes_val = int(interval_minutes)
                    max_investment_val = int(max_investment)
                    max_trading_count_val = int(max_trading_count)
                    
                    # 설정 저장
                    st.session_state.auto_trader_settings.update({
                        'interval_minutes': interval_minutes_val,
                        'max_investment': max_investment_val,
                        'max_trading_count': max_trading_count_val,
                        'risk_level': risk_style
                    })
                    
                    # 자동 거래 에이전트 생성 및 시작
                    if 'upbit_access_key' not in st.session_state or not st.session_state.upbit_access_key:
                        st.error("Upbit API 키가 설정되지 않았습니다. API 설정 탭에서 설정해주세요.")
                    elif 'upbit_secret_key' not in st.session_state or not st.session_state.upbit_secret_key:
                        st.error("Upbit Secret 키가 설정되지 않았습니다. API 설정 탭에서 설정해주세요.")
                    elif 'openai_key' not in st.session_state or not st.session_state.openai_key:
                        st.error("OpenAI API 키가 설정되지 않았습니다. API 설정 탭에서 설정해주세요.")
                    else:
                        # 자동 거래 에이전트 생성
                        if st.session_state.auto_trader is None:
                            st.session_state.auto_trader = AutoTrader(
                                access_key=st.session_state.upbit_access_key,
                                secret_key=st.session_state.upbit_secret_key,
                                model_options=st.session_state.model_options,
                                interval_minutes=interval_minutes_val,
                                max_investment=max_investment_val,
                                max_trading_count=max_trading_count_val
                            )
                            
                            # 거래 기록을 채팅창에 전송하는 콜백 함수 설정
                            def trade_callback(trade_info):
                                action = "매수" if trade_info.get("action") == "buy" else "매도"
                                timestamp = trade_info.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                                ticker = trade_info.get("ticker", "")
                                amount = trade_info.get("amount", "")
                                reason = trade_info.get("reason", "")
                                
                                trade_message = f"""
                                ## 자동 거래 알림
                                - 시간: {timestamp}
                                - 행동: {action}
                                - 코인: {ticker}
                                - 금액/수량: {amount}
                                - 이유: {reason}
                                """
                                
                                # 메시지에 추가
                                st.session_state.messages.append({"role": "assistant", "content": trade_message})
                            
                            # 자동 거래 에이전트에 콜백 등록
                            st.session_state.auto_trader.set_trade_callback(trade_callback)
                            
                        # 자동 거래 에이전트 시작
                        success = st.session_state.auto_trader.start()
                        if success:
                            st.success("자동 거래가 시작되었습니다!")
                            
                            # 시스템 메시지를 채팅창에 추가
                            system_message = f"""
                            ## 자동 거래 시작
                            자동 거래 에이전트가 시작되었습니다.
                            
                            ### 설정 정보
                            - 분석 간격: {interval_minutes_val}분
                            - 일일 최대 거래 횟수: {max_trading_count_val}회
                            - 최대 투자 금액: {max_investment_val:,}원
                            - 위험 성향: {risk_style}
                            
                            에이전트는 {interval_minutes_val}분 간격으로 시장을 분석하고 자동으로 매수/매도를 진행합니다.
                            거래 내역은 이 채팅창에 표시됩니다.
                            """
                            
                            st.session_state.messages.append({"role": "assistant", "content": system_message})
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("자동 거래 시작에 실패했습니다.")
                except ValueError:
                    st.error("입력값이 올바르지 않습니다. 숫자만 입력해주세요.")
                
        with auto_trader_control_col2:
            if st.button("자동 거래 중지", key="stop_auto_trader", use_container_width=True,
                        disabled=(st.session_state.auto_trader is None or not st.session_state.auto_trader.is_running)):
                if st.session_state.auto_trader:
                    success = st.session_state.auto_trader.stop()
                    if success:
                        st.success("자동 거래가 중지되었습니다!")
                        
                        # 시스템 메시지를 채팅창에 추가
                        system_message = """
                        ## 자동 거래 중지
                        자동 거래 에이전트가 중지되었습니다.
                        """
                        
                        st.session_state.messages.append({"role": "assistant", "content": system_message})
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("자동 거래 중지에 실패했습니다.")
        
        # 자동 거래 상태 표시
        if st.session_state.auto_trader:
            status_info = st.session_state.auto_trader.get_status()
            
            st.subheader("자동 거래 상태")
            
            status_col1, status_col2, status_col3 = st.columns(3)
            
            with status_col1:
                st.metric(
                    "상태", 
                    status_info["status"], 
                    delta="실행 중" if status_info["is_running"] else "중지됨",
                    delta_color="normal" if status_info["is_running"] else "off"
                )
            
            with status_col2:
                next_check = "준비 중..." 
                time_until = ""
                if status_info["next_check"]:
                    next_check = status_info["next_check"]
                    # n분 후 표시 추가
                    try:
                        next_time = datetime.strptime(status_info["next_check"], "%Y-%m-%d %H:%M:%S")
                        now = datetime.now()
                        if next_time > now:
                            minutes_left = (next_time - now).total_seconds() // 60
                            time_until = f"{int(minutes_left)}분 후"
                    except:
                        pass
                st.metric("다음 분석 시간", next_check, delta=time_until if time_until else None)
            
            with status_col3:
                st.metric(
                    "일일 거래 횟수", 
                    f"{status_info['daily_trading_count']} / {status_info['max_trading_count']}"
                )
            
            # 진행 바 (다음 분석까지 남은 시간)
            if status_info["is_running"] and status_info["next_check"]:
                try:
                    next_time = datetime.strptime(status_info["next_check"], "%Y-%m-%d %H:%M:%S")
                    now = datetime.now()
                    
                    if next_time > now:
                        total_seconds = status_info["interval_minutes"] * 60
                        elapsed = total_seconds - (next_time - now).total_seconds()
                        progress = min(1.0, max(0.0, elapsed / total_seconds))
                        
                        st.progress(progress)
                    else:
                        st.progress(1.0)
                except:
                    st.progress(0.0)
            else:
                st.progress(0.0)
        else:
            st.info("자동 거래 에이전트가 초기화되지 않았습니다. 설정을 구성하고 '자동 거래 시작' 버튼을 눌러주세요.")
        


        