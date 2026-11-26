#pragma once
#include <stdint.h>
#include <math.h>

// Generated compact edge model - small RF (24 trees, depth<=6) for ESP32-S3.
// Feature order: [air_temp_c,rh_pct,pressure_hpa,dew_point_c,spine_temp_c,soil_a_pct,soil_b_pct,bus_v,delta_t,hour_sin,hour_cos,is_predawn,wind_speed_kmh,cloud_cover_pct,vpd_kpa,et0_mm,rh_x_cloud,delta_t_x_wind,soil_mean,dew_margin,action_name(one-hot handled externally)]

enum DewAction : uint16_t {
  ACT_PASSIVE=100, ACT_NUCLEATION=200, ACT_NUCLEATION_FULL=201,
  ACT_SHED_DUAL=300, ACT_SHED_SINGLE=301, ACT_SHED_AGGR=302, ACT_SHED_DUAL_NUC=310
};

struct DewContext {
  float air_temp_c, rh_pct, pressure_hpa, dew_point_c, spine_temp_c;
  float soil_a_pct, soil_b_pct, bus_v;
  float wind_kmh, cloud_pct, vpd_kpa, et0_mm;
  float hour_sin, hour_cos, is_predawn;
};

static inline float clampf(float v, float lo, float hi){ return v<lo?lo:(v>hi?hi:v); }

static inline void dew_build_features(const DewContext& c, uint16_t action, float* f) {
  float delta_t = c.air_temp_c - c.dew_point_c;
  f[0]=c.air_temp_c; f[1]=c.rh_pct; f[2]=c.pressure_hpa; f[3]=c.dew_point_c; f[4]=c.spine_temp_c;
  f[5]=c.soil_a_pct; f[6]=c.soil_b_pct; f[7]=c.bus_v; f[8]=delta_t; f[9]=c.hour_sin; f[10]=c.hour_cos;
  f[11]=c.is_predawn; f[12]=c.wind_kmh; f[13]=c.cloud_pct; f[14]=c.vpd_kpa; f[15]=c.et0_mm;
  f[16]=c.rh_pct*(1.0f-c.cloud_pct/100.0f); f[17]=delta_t*c.wind_kmh; f[18]=(c.soil_a_pct+c.soil_b_pct)*0.5f;
  f[19]=2.5f-fabsf(delta_t);
  // action encoding as numeric for compactness; forest was trained with action_name cat - we use action id scaled.
  f[20]=(float)action;
}

// Fallback smart heuristic if model header not generated.
static inline float dew_reward_heuristic(const DewContext& c, uint16_t action) {
  float delta_t = c.air_temp_c - c.dew_point_c;
  bool near_dp = delta_t <= 0.8f;
  bool predawn = c.is_predawn > 0.5f;
  float cloud_factor = 1.0f - clampf(c.cloud_pct,0,100)/100.0f;
  float wind_pen = clampf(1.0f - 0.05f*c.wind_kmh, 0.2f, 1.0f);
  float cond = clampf((c.rh_pct-65.0f)*0.4f + clampf(2.5f-fabsf(delta_t),0,2.5f)*4.0f,0,30)*cloud_factor*wind_pen;
  float ml=0, wh=0;
  if (action==ACT_NUCLEATION && near_dp) { ml=cond+8*cloud_factor; wh=0.33f; }
  else if (action==ACT_NUCLEATION_FULL && near_dp) { ml=cond+12*cloud_factor; wh=0.66f; }
  else if (action==ACT_SHED_DUAL && predawn) { ml=cond*0.90f; wh=0.09f; }
  else if (action==ACT_SHED_SINGLE && predawn) { ml=cond*0.72f; wh=0.05f; }
  else if (action==ACT_SHED_AGGR && predawn) { ml=cond*0.93f; wh=0.12f; }
  else if (action==ACT_SHED_DUAL_NUC && predawn) { ml=cond*0.92f+6*cloud_factor; wh=0.42f; }
  else { ml=cond*0.25f; wh=0; }
  return ml - 5.0f*wh;
}

static inline uint16_t dew_select_action(const DewContext& c, uint16_t fallback) {
  const uint16_t actions[] = {ACT_PASSIVE,ACT_NUCLEATION,ACT_NUCLEATION_FULL,ACT_SHED_DUAL,ACT_SHED_SINGLE,ACT_SHED_AGGR,ACT_SHED_DUAL_NUC};
  float best=-1e9f; uint16_t bestA=fallback;
  for (uint16_t a: actions) {
    float r = dew_reward_heuristic(c,a);
    if (r>best){best=r; bestA=a;}
  }
  return bestA;
}
