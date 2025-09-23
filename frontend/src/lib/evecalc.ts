export type Activity = 'Manufacturing' | 'Reactions'

export type Bom = { name: string; qty: number }[]

export type Skills = {
  industry: number // 0-5
  advancedIndustry: number // 0-5
  reactions: number // 0-5
}

export type Structure = {
  name: string
  activity: Activity
  meBonus: number // 0..0.5 (e.g., 0.02 for 2%)
  teBonus: number // 0..0.5
  rigs: string[]
}

export type CalcInput = {
  bom: Bom
  baseRunTimeMin: number
  activity: Activity
  skills: Skills
  structure: Structure
  group?: 'AdvComponents' | 'T2SmallShips' | 'T2MediumShips'
}

export type CalcOutput = {
  adjustedBom: { name: string; qty: number }[]
  runTimeMin: number
}

const clamp = (v: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, v))

export function computeMaterialsAndTime(input: CalcInput): CalcOutput {
  const { bom, baseRunTimeMin, activity, skills, structure } = input
  // Apply group-aware ME bonus: simple canonical approximations
  let groupMeBonus = 0
  if (activity === 'Manufacturing') {
    if (input.group === 'AdvComponents') groupMeBonus = 0.02
    if (input.group === 'T2SmallShips') groupMeBonus = 0.02
    if (input.group === 'T2MediumShips') groupMeBonus = 0.02
  }
  const me = clamp(structure.meBonus + groupMeBonus, 0, 0.5)
  const adjustedBom = bom.map((item) => ({
    name: item.name,
    qty: Math.max(0, Math.ceil(item.qty * (1 - me)))
  }))

  let timeMult = 1
  if (activity === 'Manufacturing') {
    timeMult *= 1 - 0.04 * clamp(skills.industry, 0, 5)
    timeMult *= 1 - 0.03 * clamp(skills.advancedIndustry, 0, 5)
  } else {
    // Reactions placeholder: assume 4% per Reactions level
    timeMult *= 1 - 0.04 * clamp(skills.reactions, 0, 5)
  }
  // TE: structure bonus plus small extra for group (placeholder)
  let groupTeBonus = 0
  if (activity === 'Manufacturing') {
    if (input.group === 'AdvComponents') groupTeBonus = 0.01
    if (input.group === 'T2SmallShips') groupTeBonus = 0.01
    if (input.group === 'T2MediumShips') groupTeBonus = 0.01
  }
  timeMult *= 1 - clamp(structure.teBonus + groupTeBonus, 0, 0.5)
  timeMult = clamp(timeMult, 0.4, 1)
  const runTimeMin = Math.max(1, Math.round(baseRunTimeMin * timeMult))

  return { adjustedBom, runTimeMin }
}
