# My Reflection on This Task

It was a great task. I loved what I built and I learned a lot from it, how to
handle errors and how to search for something I did not know before. But
everything has a hard point, so:

## What was the hardest part

Getting the service authenticated against ServiceNow.

Everything else went the way I expected. The webhook worked, Gemini answered
with the right decision for all three test tickets, and the Business Rule fired
the moment a ticket was created. But every write back came back with
`401 Unauthorized`, and the body only said "User is not authenticated", which
does not tell you what is actually wrong.

What made it confusing is that the same instance worked fine everywhere else. I
could log in as `admin` in the browser, and the REST API Explorer returned data
with no problem. So it looked like my credentials were correct and my Python was
wrong. I checked the code many times, printed the password to be sure it was not
empty, decoded the `Authorization` header to confirm basic auth was really being
sent, and compared my `servicenow.py` against a working one from someone else.
It was the same code.

What I was missing is that the REST API Explorer runs on my browser session, not
on my password. Two different ways in, and only one of them was broken.

After a lot of searching and reading about ServiceNow roles I found the real
cause. Being `admin` in the UI is not enough for the REST API, the user needs
its own roles for it, and the `admin` user also had **Password reset required**
ticked, which makes the API refuse the password even when it is correct. Adding
`snc_basic_auth_api_access`, `snc_platform_rest_api_access`, `security_admin`
and `snc_required_script_writer_permission`, and unticking that box, fixed it
immediately.

The lesson I take from it is to check what a test actually proves before
trusting it. I lost hours because the browser working made me think the
credentials were fine, so I kept looking in the wrong place.

## What I would improve with more time

**Security.** Right now anyone who finds the ngrok URL can post to `/webhook`
and make the agent write on a ticket. It needs a shared secret that the service
checks on every request, and a dedicated integration user with only the roles it
needs, not `admin`.

**Answering the follow up on an `ask`.** This is the gap that bothers me most.
When the agent chooses `ask` it writes one question in `comments` and stops
there. If the user comes back and answers it, nothing happens, the Business Rule
only fires on insert, the webhook drops a second call for the same `sys_id` as a
duplicate, and the payload does not carry the comments at all, so Gemini would
never see the answer anyway. To close that loop the rule has to run on update
too, with a condition on the comments changing and on the author not being the
integration user so the agent does not reply to itself, the payload has to carry
the conversation so far, and the prompt has to read it before deciding, so a
question that was answered can turn into `respond` instead of asking again.

**A full UI.** A page to submit tickets and follow them, with two roles, a user
who sees only their own tickets and the answers, and an agent who sees the work
notes and everything escalated. Then nobody needs the ServiceNow interface.

**A bigger knowledge base, and retrieval with it.** Five articles fit in the
prompt. A hundred will not, and that is where I would add embeddings and send
only the relevant ones, and where a framework like LangChain starts to be worth
its weight instead of just adding a dependency.

**Surviving restarts and outages.** The duplicate guard is a set in memory, so
it is empty again after a restart and belongs in a small database. Failures
should also be retried with a backoff instead of going straight to `escalate`,
because both failures I actually hit, a Gemini rate limit and a sleeping
instance, fix themselves after waiting.

**Measuring the decisions.** Three test tickets are enough to demo but not to
trust. I would build a bigger set with the expected decision for each, store
every decision the agent makes, and be able to say how accurate it is instead of
guessing.

## At the end

I still think this is a good idea, not just a task I had to finish. It solves a
real problem, people waiting on a ticket for an answer that already exists
somewhere. I want to keep working on it when I have the time, and I know I will
learn a lot from taking it further.
