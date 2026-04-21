"""
Test fixtures - Sample anonymized data for testing
"""

SAMPLE_LEAD_TRANSCRIPT = """
**Meeting Date:** 19th Apr, 2026 - 7:30 AM

**Raj from Turtle** *[00:47]*: Hi Lead, thank you for taking the time.

**Lead** *[00:51]*: Hello, thank you for calling. My wife is also with me.

**Raj from Turtle** *[01:00]*: Hi both of you. So we are based out of Delhi and working on financial advisory for returning to India.

**Lead** *[02:04]*: So we've been in the US for 13-14 years. I'm working for a pharmaceutical company and my wife is a data scientist. We're planning to move back after our second child is born, who will be one year old soon. Our first one is five years old in June.

**Raj from Turtle** *[03:41]*: Got it. When are you thinking of returning?

**Lead** *[03:51]*: Most probably by the end of this year, but could be as soon as two months. We have a house here in Indianapolis that we're planning to sell.

**Raj from Turtle** *[05:25]*: How much liquid assets do you have?

**Lead** *[05:30]*: We sold our New Jersey house for $230,000 last year. I have around 100-130k in my 401k, 10-12k in HSA, about 40-60k in savings. We also have around 5k in Robinhood and just opened a JP Morgan account with 25k.
"""


SAMPLE_CLIENT_TRANSCRIPT = """
**Meeting Date:** 3rd Apr, 2026 - 9:00 PM

**Mukund** *[00:01]*: Thank you for taking time. I'm Mukund from Turtle. I'll explain how we can help with your move back to India.

**Client** *[01:30]*: Yeah, I'm going back at the end of this month. In the next 2-3 weeks I want to close my Robinhood account, create W8-BEN forms, and sort out my E-Trade account. I have some cash reserves too.

**Mukund** *[02:34]*: Understood. You mentioned having 401k, stocks, RSUs, HSA, and bank accounts. Let me collect all account details first.

**Client** *[02:50]*: I have 401k in Fidelity, stocks and RSUs, HSA, and multiple bank accounts. I also have an ICICI NRE/NRO account I don't use.

**Mukund** *[03:53]*: We need to see which accounts support Indian addresses. Robinhood doesn't, so we'll move it to Fidelity. For HSA and 401k, you can handle those later.

**Client** *[04:20]*: I do have a friend for US address and I'm keeping my US number for at least 2 years.

**Mukund** *[10:44]*: I see you mentioned wanting to buy a plot of land. What budget?

**Client** *[10:58]*: Around 5 crores.

**Mukund** *[18:10]*: Great. We'll plan for that transfer. What city are you moving to?

**Client** *[26:23]*: Chennai.
"""
