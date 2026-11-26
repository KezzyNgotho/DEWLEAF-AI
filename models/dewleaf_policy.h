#pragma once
#include <stdint.h>

// Generated from Phase 0 training data. Replace with TFLM for full nonlinear edge inference.
struct DewLeafActionScore {
  uint16_t action_id;
  float reward_bias;
};

static const float DEWLEAF_LAMBDA_WH = 5.0f;
static const uint8_t DEWLEAF_ACTION_COUNT = 5;
static const DewLeafActionScore DEWLEAF_ACTION_SCORES[] = {
  { 200, -0.070f }, // nucleation_assist, mean_reward=4.517
  { 100, 0.000f }, // passive_only, mean_reward=4.588
  { 302, -0.342f }, // shed_aggressive, mean_reward=4.245
  { 300, -0.513f }, // shed_dual, mean_reward=4.075
  { 301, -0.320f }, // shed_single_explore, mean_reward=4.268
};

static inline uint16_t dewleaf_select_action(uint16_t fallback_action_id) {
  uint16_t best = fallback_action_id;
  float best_bias = -1e9f;
  for (uint8_t i = 0; i < DEWLEAF_ACTION_COUNT; i++) {
    if (DEWLEAF_ACTION_SCORES[i].reward_bias > best_bias) {
      best_bias = DEWLEAF_ACTION_SCORES[i].reward_bias;
      best = DEWLEAF_ACTION_SCORES[i].action_id;
    }
  }
  return best;
}
