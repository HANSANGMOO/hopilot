/**
 * 웹소켓이라는 물리적 네트워크 기술에 전혀 의존하지 않고,
 * 순수한 데이터 직렬화(Serialization)와 파싱(Parsing) 논리만 담당하는 채널 계층입니다.
 *
 * 파이썬 백엔드의 `python/core/channel.py`와 완벽하게 대칭을 이루는 클래스입니다.
 */
export class Channel {
  /**
   * 생성자를 통해 외부(FastAPIClient)로부터 네트워크 기능을 주입(Dependency Injection) 받습니다.
   * 이렇게 하면 이 파일 안에는 'WebSocket'이라는 단어가 단 한 번도 등장하지 않습니다!
   *
   * @param sendMsgFunc 문자열을 네트워크 밖으로 던지는 함수
   * @param onReceiveRegister 외부에서 수신된 데이터를 이 채널의 콜백으로 밀어 넣어주도록 등록하는 함수
   * @param onMessageParsed 파싱(JSON.parse)이 완료된 예쁜 객체를 React로 보내기 위해 호출할 함수
   */
  constructor(
    private sendMsgFunc: (text: string) => void,
    onReceiveRegister: (callback: (text: string) => void) => void,
    private onMessageParsed: (payload: any) => void
  ) {
    // 생성과 동시에 수신 파이프라인(리스너)을 등록합니다. (파이썬의 listen 루프 대체)
    onReceiveRegister((rawText: string) => {
      this.handleReceive(rawText)
    })
  }

  /**
   * 프론트엔드(React)에서 온 데이터를 파이썬 서버로 보낼 때 호출합니다.
   * JSON 직렬화를 수행한 후, 주입받은 송신 함수를 통해 밖으로 던집니다.
   */
  public send(payload: any): void {
    try {
      const jsonStr = JSON.stringify(payload)
      this.sendMsgFunc(jsonStr)
    } catch (error) {
      console.error('[Channel] 데이터 직렬화 실패:', error)
    }
  }

  /**
   * 네트워크로부터 텍스트를 받았을 때 호출되는 내부 메서드입니다.
   */
  private handleReceive(rawText: string): void {
    try {
      const payload = JSON.parse(rawText)

      // 파싱된 최종 객체를 최종 목적지(FastAPIClient)로 전달합니다.
      this.onMessageParsed(payload)
    } catch (error) {
      console.error('[Channel] 수신된 JSON 파싱 실패:', rawText, error)
    }
  }
}
