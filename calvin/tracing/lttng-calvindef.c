#define TRACEPOINT_DEFINE
#include "lttng-calvindef.h"

void lttng_calvin_actor_fire_enter(const char * actor_id) { tracepoint(com_ericsson_calvin, actor_fire_enter, actor_id); }
void lttng_calvin_actor_fire_exit(const char * actor_id) { tracepoint(com_ericsson_calvin, actor_fire_exit, actor_id); }
void lttng_calvin_actor_method_fire(const char * actor_id, const char * method_id) { tracepoint(com_ericsson_calvin, actor_method_fire, actor_id, method_id); }
void lttng_calvin_actor_method_fire_d(const char * actor_id, const char * method_id, double value) { tracepoint(com_ericsson_calvin, actor_method_fire_d, actor_id, method_id, value); }
void lttng_calvin_actor_method_fire_dd(const char * actor_id, const char * method_id, double value1, double value2) { tracepoint(com_ericsson_calvin, actor_method_fire_dd, actor_id, method_id, value1, value2); }
void lttng_calvin_queue_minmax(const char * actor_id, const char * method_id, int value1, int value2) { tracepoint(com_ericsson_calvin, queue_minmax, actor_id, method_id, value1, value2); }
void lttng_calvin_actor_migrate(const char * actor_id) { tracepoint(com_ericsson_calvin, actor_migrate, actor_id); }
void lttng_calvin_actor_migrated(const char * actor_id) { tracepoint(com_ericsson_calvin, actor_migrated, actor_id); }
void lttng_calvin_queue_precond(const char * actor, const char * queue, int discarded, double off) { tracepoint(com_ericsson_calvin, queue_precond, actor, queue, discarded, off); }
void lttng_calvin_actor_method_fire_dddd(const char * actor_id, const char * method_id, double value1, double value2, double value3, double value4) { tracepoint(com_ericsson_calvin, actor_method_fire_dddd, actor_id, method_id, value1, value2, value3, value4); }
void lttng_calvin_actor_method_fire_ddd(const char * actor_id, const char * method_id, double value1, double value2, double value3) { tracepoint(com_ericsson_calvin, actor_method_fire_ddd, actor_id, method_id, value1, value2, value3); }
