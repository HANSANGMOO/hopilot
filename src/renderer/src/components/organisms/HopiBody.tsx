import Hopi from '../atoms/Hopi'

export default function HopiBody() {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-6 p-8 pb-32">
      <Hopi />
      <div className="text-center">
        <h1 className="text-lg font-medium text-text-secondary">
          안녕하세요! 저는 Hopilot입니다.
        </h1>
      </div>
    </div>
  )
}
