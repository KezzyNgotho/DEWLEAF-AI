#pragma once
#include <stdint.h>

// Generated from DewLeaf training data. Biases are empirical mean rewards relative to passive_only.
// For full nonlinear edge inference, use exported TFLM model artifact alongside this fallback.
struct DewLeafActionScore { uint16_t action_id; float reward_bias; };

static const float DEWLEAF_LAMBDA_WH = 5.0f;
static const uint8_t DEWLEAF_ACTION_COUNT = 5;
static const DewLeafActionScore DEWLEAF_ACTION_SCORES[] = {
  { 200, -1.6558f }, // nucleation_assist, mean_reward=-1.547
  { 100, 0.0000f }, // passive_only, mean_reward=0.109
  { 302, 119.9413f }, // shed_aggressive, mean_reward=120.050
  { 300, 28.1686f }, // shed_dual, mean_reward=28.278
  { 301, 77.3233f }, // shed_single_explore, mean_reward=77.432
};

static inline uint16_t dewleaf_select_action(uint16_t fallback_action_id) {
  uint16_t best = fallback_action_id; float best_bias = -1e9f;
  for (uint8_t i = 0; i < DEWLEAF_ACTION_COUNT; i++) {
    if (DEWLEAF_ACTION_SCORES[i].reward_bias > best_bias) {
      best_bias = DEWLEAF_ACTION_SCORES[i].reward_bias; best = DEWLEAF_ACTION_SCORES[i].action_id;
    }
  }
  return best;
}
