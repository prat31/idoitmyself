/** Label colour palette. Keys match the backend; classes map to the --label-* tokens in index.css. */
export const labelColors = ['gray', 'red', 'orange', 'amber', 'green', 'teal', 'blue', 'violet', 'pink'] as const

export type LabelColor = (typeof labelColors)[number]

export const labelColorClass: Record<LabelColor, string> = {
  gray: 'bg-label-gray',
  red: 'bg-label-red',
  orange: 'bg-label-orange',
  amber: 'bg-label-amber',
  green: 'bg-label-green',
  teal: 'bg-label-teal',
  blue: 'bg-label-blue',
  violet: 'bg-label-violet',
  pink: 'bg-label-pink',
}

export const labelColorName: Record<LabelColor, string> = {
  gray: 'Gray',
  red: 'Red',
  orange: 'Orange',
  amber: 'Amber',
  green: 'Green',
  teal: 'Teal',
  blue: 'Blue',
  violet: 'Violet',
  pink: 'Pink',
}
