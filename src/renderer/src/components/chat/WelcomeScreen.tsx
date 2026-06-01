export default function WelcomeScreen() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center p-8 pb-32">
      <div className="space-y-3 text-center">
        <h1 className="text-3xl font-semibold text-gray-200">안녕하세요! 저는 Hopilot입니다.</h1>
        <p className="text-sm text-gray-400">
          아래 입력창에 메시지를 입력하여 자유롭게 대화를 시작해 보세요.
        </p>
      </div>
    </div>
  )
}
