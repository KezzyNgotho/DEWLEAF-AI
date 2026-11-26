#pragma once
#include <stdint.h>

// Generated from DewLeaf training data. Biases are empirical mean rewards relative to passive_only.
// For full nonlinear edge inference, use exported TFLM model artifact alongside this fallback.
struct DewLeafActionScore { uint16_t action_id; float reward_bias; };

static const float DEWLEAF_LAMBDA_WH = 5.0f;
static const uint8_t DEWLEAF_ACTION_COUNT = 7;
static const DewLeafActionScore DEWLEAF_ACTION_SCORES[] = {
  { 200, 0.0320f }, // nucleation_assist, mean_reward=0.079
  { 201, -0.2191f }, // nucleation_full, mean_reward=-0.172
  { 100, 0.0000f }, // passive_only, mean_reward=0.047
  { 302, 6.5242f }, // shed_aggressive, mean_reward=6.572
  { 300, 2.7149f }, // shed_dual, mean_reward=2.762
  { 310, 4.6391f }, // shed_dual_nucleation, mean_reward=4.686
  { 301, 1.8894f }, // shed_single_explore, mean_reward=1.937
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
