# How to give a task (you never write code)

You have 3 ways. Way 1 is the normal one.

## Way 1: Tell me in chat, in plain words (best)

Example: "Open this site, search for X, click the first result, play it for 30 seconds."

What happens:
1. I send ONE scout user to the site first. The scout finds the real buttons and fields.
2. I show you the steps in plain English.
3. You say go, or fix a step.
4. I save the steps as `task.json` and launch the swarm at the size you picked.

You never see or write the step file unless you want to.

## Way 2: Do it once yourself, the recorder writes the steps

On your Mac, one command opens a browser with a recorder:

```
playwright codegen https://the-site.com
```

Do the task once with your own mouse, then close the window.
Send me the saved recording file. The converter turns it into steps:

```
python3 codegen_to_task.py recording.py task.json
```

Good when the site is hard to describe in words.

## Way 3: Write steps by hand (only if you want)

`task.json` is a small list. Step types: goto, click, click_text, fill,
fill_placeholder, press, wait, scroll, play_media, download.
Nobody needs this way. It exists so the system stays open and checkable.

## One limit, plain

If a task needs a login, the swarm needs accounts to log in with.
No login is invented by the system. Tell me how accounts are handled
for your task and we plan that part before launch.
