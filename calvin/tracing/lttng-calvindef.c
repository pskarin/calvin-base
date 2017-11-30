#define TRACEPOINT_DEFINE
#include "lttng-calvindef.h"

void lttng_calvin_actor_fire(int x) { tracepoint(com_ericsson_calvin, actor_fire, x); }
