/**
 * 프론트엔드(Electron)와 백엔드(Python) 간의 통신(웹소켓 등)에서
 * 가장 기본이 되는 최상위 시그널(이벤트) 인터페이스입니다.
 */
export interface HOSignalBase {
  /**
   * 시그널의 고유 이름 (라우팅 식별자)
   * 파이썬 객체 이름과 일치해야 합니다.
   */
  type: string

  /**
   * 이 시그널 객체를 백엔드로 발사합니다.
   */
  emit(): void
}

/**
 * 프론트엔드용 시그널 팩토리(Factory) 함수입니다.
 * 반복되는 보일러플레이트 코드를 없애고, 단 한 줄로 완벽한 타입 추론이 가능한 시그널을 생성합니다.
 *
 * @param type 파이썬 백엔드에서 받을 시그널의 클래스 이름 (예: "SendMessageSignal")
 * @returns payload를 인자로 받아 emit() 메서드가 탑재된 시그널 객체를 반환하는 생성 함수
 */
export function defineSignal<Payload = void>(type: string) {
  // 제네릭으로 받은 Payload 타입에 맞춰서 인자를 받습니다.
  // 데이터가 없는 void 타입일 경우 인자를 비울 수 있도록 선택적(?)으로 받습니다.
  return (payload?: Payload) => {
    const signal = {
      // 1. 팩토리가 런타임에 몰래 type을 주입합니다.
      type,

      // 2. 개발자가 넘겨준 데이터(Payload)를 합칩니다. (데이터가 없으면 무시)
      ...(payload || {}),

      // 3. 발사 버튼(emit)을 탑재합니다.
      emit: function () {
        // TypeScript 에러 방지를 위해 any 캐스팅 후 Preload API 호출
        const api = (window as any).api
        if (api && api.sendSignal) {
          api.sendSignal(this)
        } else {
          // Preload 연결 전 디버깅을 위한 콘솔 출력
          console.warn(
            `[Emit 발사됨] ${type}: 하지만 window.api.sendSignal이 아직 연결되지 않았습니다.`,
            this
          )
        }
      }
    }

    // 최종적으로 HOSignalBase와 개발자가 넘겨준 Payload 타입이 결합된 객체로 인식하게 만듭니다.
    return signal as HOSignalBase & Payload
  }
}

/**
 * [사용 예시 가이드]
 *
 * 1. 데이터가 있는 시그널 정의
 * export const SendMessageSignal = defineSignal<{ text: string }>("SendMessageSignal");
 *
 * 2. 데이터가 없는 시그널(트리거) 정의
 * export const StopGenerationSignal = defineSignal<void>("StopGenerationSignal");
 *
 * 3. 쏠 때 (어느 컴포넌트에서나 즉시 사용)
 * SendMessageSignal({ text: "안녕" }).emit();
 * StopGenerationSignal().emit();
 */
