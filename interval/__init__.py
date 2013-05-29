from datetime import timedelta

try:
    from psycopg2_dateutils import psycopg2_dateutils
    from dateutil.relativedelta import relativedelta
    HAVE_RELATIVEDELTA = True
    # relativedelta seems to transform 60 minutes to one hour. so we need minutes and hours as well
    DELTA_ATTRIBUTES = ('years', 'months', 'days', 'hours', 'minutes', 'seconds', 'microseconds')
except:
    HAVE_RELATIVEDELTA = False
    DELTA_ATTRIBUTES = ('days', 'seconds', 'microseconds')

def is_delta(value):
	return isinstance(value, timedelta) or (HAVE_RELATIVEDELTA and isinstance(value, relativedelta))