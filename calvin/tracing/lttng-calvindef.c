#define TRACEPOINT_DEFINE
#include "lttng-calvindef.h"

void lttng_calvin_actor_fire_enter(const char * actor_id) { tracepoint(com_ericsson_calvin, actor_fire_enter, actor_id); }
void lttng_calvin_actor_fire_exit(const char * actor_id) { tracepoint(com_ericsson_calvin, actor_fire_exit, actor_id); }
void lttng_calvin_actor_method_fire(const char * actor_id, const char * method_id, int hasvalue, double value) {
  tracepoint(com_ericsson_calvin, actor_method_fire, actor_id, method_id, hasvalue, value);
}
