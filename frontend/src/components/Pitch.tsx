import type { ReactNode } from "react"
import { toSvg } from "@/lib/pitchCoordinates"

type PitchProps = {
  className?: string
  children?: ReactNode
}

function FieldRect({
  x,
  y,
  width,
  height,
}: {
  x: number
  y: number
  width: number
  height: number
}) {
  const topLeft = toSvg(x, y + height)
  return <rect x={topLeft.x} y={topLeft.y} width={width} height={height} />
}

function FieldLine({
  x1,
  y1,
  x2,
  y2,
}: {
  x1: number
  y1: number
  x2: number
  y2: number
}) {
  const start = toSvg(x1, y1)
  const end = toSvg(x2, y2)
  return <line x1={start.x} y1={start.y} x2={end.x} y2={end.y} />
}

function Spot({ x, y, radius }: { x: number; y: number; radius: number }) {
  const point = toSvg(x, y)
  return <circle cx={point.x} cy={point.y} r={radius} />
}

function PenaltyArc({ right = false }: { right?: boolean }) {
  const topY = 34 + Math.sqrt(9.15 ** 2 - 5.5 ** 2)
  const bottomY = 34 - Math.sqrt(9.15 ** 2 - 5.5 ** 2)
  const x = right ? 88.5 : 16.5
  const controlX = right ? 84.85 : 20.15
  const start = toSvg(x, topY)
  const control = toSvg(controlX, 34)
  const end = toSvg(x, bottomY)
  return (
    <path
      d={`M ${start.x} ${start.y} Q ${control.x} ${control.y} ${end.x} ${end.y}`}
    />
  )
}

export default function Pitch({ className, children }: PitchProps) {
  const center = toSvg(52.5, 34)
  return (
    <svg
      aria-label="Sân bóng đá theo hệ tọa độ chuẩn, đơn vị mét"
      className={className}
      preserveAspectRatio="xMidYMid meet"
      role="img"
      viewBox="0 0 105 68"
    >
      <defs>
        <pattern
          height="68"
          id="pitch-grass"
          patternUnits="userSpaceOnUse"
          width="21"
        >
          <rect fill="#153522" height="68" width="10.5" x="0" y="0" />
          <rect fill="#183b27" height="68" width="10.5" x="10.5" y="0" />
        </pattern>
      </defs>
      <rect fill="url(#pitch-grass)" height="68" rx="1" width="105" />
      <g
        className="pitch-markings"
        fill="none"
        stroke="white"
        strokeOpacity="0.6"
        strokeWidth="0.22"
      >
        <FieldRect height={68} width={105} x={0} y={0} />
        <FieldLine x1={52.5} x2={52.5} y1={0} y2={68} />
        <circle cx={center.x} cy={center.y} r="9.15" />
        <circle cx={center.x} cy={center.y} fill="white" r="0.25" />
        <FieldRect height={40.32} width={16.5} x={0} y={13.84} />
        <FieldRect height={40.32} width={16.5} x={88.5} y={13.84} />
        <FieldRect height={18.32} width={5.5} x={0} y={24.84} />
        <FieldRect height={18.32} width={5.5} x={99.5} y={24.84} />
        <Spot radius={0.25} x={11} y={34} />
        <Spot radius={0.25} x={94} y={34} />
        <PenaltyArc />
        <PenaltyArc right />
        <FieldLine x1={0} x2={2.44} y1={30.34} y2={30.34} />
        <FieldLine x1={2.44} x2={2.44} y1={30.34} y2={37.66} />
        <FieldLine x1={0} x2={2.44} y1={37.66} y2={37.66} />
        <FieldLine x1={102.56} x2={105} y1={30.34} y2={30.34} />
        <FieldLine x1={102.56} x2={102.56} y1={30.34} y2={37.66} />
        <FieldLine x1={102.56} x2={105} y1={37.66} y2={37.66} />
      </g>
      <g className="pitch-overlays">{children}</g>
    </svg>
  )
}
