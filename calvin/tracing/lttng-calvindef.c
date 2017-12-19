#define TRACEPOINT_DEFINE
#include "lttng-calvindef.h"

void lttng_calvin_actor_fire_enter(const char * actor_id) { tracepoint(com_ericsson_calvin, actor_fire_enter, actor_id); }
void lttng_calvin_actor_fire_exit(const char * actor_id) { tracepoint(com_ericsson_calvin, actor_fire_exit, actor_id); }
void lttng_calvin_actor_method_fire(const char * actor_id, const char * method_id) { tracepoint(com_ericsson_calvin, actor_method_fire, actor_id, method_id); }
void lttng_calvin_actor_method_fire_d(const char * actor_id, const char * method_id, double value) { tracepoint(com_ericsson_calvin, actor_method_fire_d, actor_id, method_id, value); }
void lttng_calvin_actor_method_fire_dd(const char * actor_id, const char * method_id, double value1, double value2) { tracepoint(com_ericsson_calvin, actor_method_fire_dd, actor_id, method_id, value1, value2); }
