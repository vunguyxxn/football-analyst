export type SvgPoint = { x: number; y: number }

export function toSvg(x_m: number, y_m: number): SvgPoint {
  return { x: x_m, y: 68 - y_m }
}
