from datetime import datetime, timedelta
from wsgiref.handlers import format_date_time

def gen_search_expires() -> str:
    """Generate expires in RFC 1123 format.
       RFC 1123 format ex 'Wed, 21 Oct 2015 07:28:00 GMT'

       Set to 10 minutes in case results change
    """
    now=datetime.now()
    expire = now + timedelta(minutes=10)
    expires = format_date_time(expire.timestamp())
    return expires