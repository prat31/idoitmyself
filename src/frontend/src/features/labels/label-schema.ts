import { z } from 'zod'

import { labelColors } from './colors'
import { FILTER_CONDITION_MAX } from './filter-condition'

/** Fields shared by the add and edit dialogs (everything except the immutable name).
 *  Limits mirror the backend's LabelCreate / LabelUpdate validation. */
export const editableLabelFields = {
  description: z.string().trim().max(500, 'Keep the description under 500 characters'),
  color: z.enum(labelColors),
  filterCondition: z.string().trim().max(FILTER_CONDITION_MAX, 'Keep the filter condition under 2000 characters'),
  matchThreshold: z
    .number({ error: 'Enter a number between 0 and 1' })
    .gt(0, 'Must be greater than 0')
    .lt(1, 'Must be less than 1'),
}

export const DEFAULT_MATCH_THRESHOLD = 0.5
