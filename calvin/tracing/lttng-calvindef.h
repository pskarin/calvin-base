#undef TRACEPOINT_PROVIDER
#define TRACEPOINT_PROVIDER com_ericsson_calvin

#undef TRACEPOINT_INCLUDE
#define TRACEPOINT_INCLUDE "lttng-calvindef.h"

#if !defined(_TP_H) || defined(TRACEPOINT_HEADER_MULTI_READ)
#define _TP_H

#include <lttng/tracepoint.h>

/*
 * Use TRACEPOINT_EVENT(), TRACEPOINT_EVENT_CLASS(),
 * TRACEPOINT_EVENT_INSTANCE(), and TRACEPOINT_LOGLEVEL() here.
 */

#endif /* _TP_H */

#include <lttng/tracepoint-event.h>

TRACEPOINT_EVENT(
    /* Tracepoint provider name */
    com_ericsson_calvin,

    /* Tracepoint name */
    actor_fire,

    /* Input arguments */
    TP_ARGS(
        int, count
    ),

    /* Output event fields */
    TP_FIELDS(
        ctf_integer(int, count, count)
    )
)
