# My Reflection on This Task

It was a great task. I loved what I built and I learned a lot from it, how to
handle errors and how to search for something I did not know before. But
everything has a hard point, so:

## What was the hardest part

Getting the service authenticated against ServiceNow.

Everything else in the loop went the way I expected. The webhook worked, Gemini
answered with the right decision for all three test tickets, and the Business
Rule fired the moment a ticket was created. 

But every write back came back with
`401 Unauthorized`, and the response body only said "User is not authenticated",
which does not tell you what is actually wrong.

What made it confusing is that the same instance worked fine everywhere else at
the same time.

I could log in as `admin` in the browser, and the REST API Explorer inside ServiceNow returned data without any problem.

So it looked like my credentials were correct and my Python code was wrong. I checked the code many times, printed the password to be sure it was not empty, decoded the `Authorization` header to confirm basic auth was really being sent, and compared my `servicenow.py` against a working one from someone else. It was the same code.

The thing I was missing is that the REST API Explorer runs on my browser
session, not on my password. A working session in the browser proves nothing
about basic auth.

Those are two different ways in, and only one of them was actually broken.

After a lot of searching and reading about ServiceNow roles I found the real
cause. 

Being `admin` in the UI is not enough for the REST API, the user needs its own roles for it, and the `admin` user 
also had **Password reset required**
ticked, which makes the API refuse the password even when the password is
correct. Adding `snc_basic_auth_api_access`, `snc_platform_rest_api_access`,
`security_admin` and `snc_required_script_writer_permission`, 
and unticking that box, fixed it immediately.

The lesson I am taking from it is to check what a test actually proves before
trusting it. I lost hours because the browser working made me think the
credentials were fine, so I kept looking in the wrong place.

## What I would improve with more time

**Security.** Right now anyone who finds the ngrok URL can post to `/webhook`
and make the agent write on a ticket. It needs a shared secret in the Business
Rule that the service checks on every request, and HTTPS only. The ServiceNow
account should also be a dedicated integration user with only the roles it
needs, not `admin`.

**A full UI.** A page to submit a ticket and follow it, with two roles, a normal
user who only sees their own tickets and the answers, and an agent who sees the
work notes and everything escalated. Then the user never needs the ServiceNow
interface at all.

**A bigger knowledge base, and retrieval with it.** Five articles fit in the
prompt easily. With a hundred they will not, and that is the point where I would
add embeddings and send only the relevant articles, and where a framework like
LangChain starts to be worth the weight instead of just adding a dependency.

**Surviving restarts and outages.** The duplicate guard is a set in memory, so
it is empty again after a restart. It should be in a small database. Failures
should also be retried with a backoff instead of falling straight to
`escalate`, because the two failures I actually hit, a Gemini rate limit and a
sleeping instance, both fix themselves after waiting.

**Measuring the decisions.** Three test tickets are enough to demo but not to
trust. I would build a bigger set with the expected decision for each, store
every decision the agent makes, and be able to say how accurate it is instead of
guessing.

## At the end

I still think this is a good idea, not just a task I had to finish. It solves a
real problem, people waiting on a ticket for an answer that already exists
somewhere, and the whole loop turned out to be smaller than I expected once I
understood every piece of it.

So I want to keep working on it when I have the time. Every part of it has
something more to learn in it, the agent side, ServiceNow, and making it safe
enough to trust with real tickets, and I know I will learn a lot from taking it
further.
