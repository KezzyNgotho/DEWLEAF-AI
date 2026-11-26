#pragma once
#include <stdint.h>

// Calibrated from measured bench data: logs/sim_bench_14night.csv
struct DewLeafActionScore { uint16_t action_id; float reward_bias; };
static const float DEWLEAF_LAMBDA_WH = 5.0f;
static const uint8_t DEWLEAF_ACTION_COUNT = 5;
static const DewLeafActionScore DEWLEAF_ACTION_SCORES[] = {
  { 200, -1.6558f }, // nucleation_assist n=112 mean=-1.547
  { 100, 0.0000f }, // passive_only n=800 mean=0.109
  { 302, 119.9413f }, // shed_aggressive n=24 mean=120.050
  { 300, 28.1686f }, // shed_dual n=127 mean=28.278
  { 301, 77.3233f }, // shed_single_explore n=29 mean=77.432
};

static inline uint16_t dewleaf_select_action(uint16_t fallback_action_id){
  uint16_t best=fallback_action_id; float best_bias=-1e9f;
  for(uint8_t i=0;i<DEWLEAF_ACTION_COUNT;i++){ if(DEWLEAF_ACTION_SCORES[i].reward_bias>best_bias){best_bias=DEWLEAF_ACTION_SCORES[i].reward_bias; best=DEWLEAF_ACTION_SCORES[i].action_id;} }
  return best;
}
