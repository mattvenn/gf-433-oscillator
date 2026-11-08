# Keeping long server runs moving (block to include in every handoff)

**Problem seen on 2026-11-07/08.** The pod agent started jobs with `nohup … &` and ended its turn. The harness
doesn't track a detached process, so nothing woke the agent when the jobs finished. The machine sat idle until Matt
asked for a status, and the laptop session didn't know results had landed either.

The rules below go into every `docs/handoff_*.md` as a section called "Running unattended". They are to be tested
on the next handoff, and anything that doesn't work gets cut.

## Rules for the server agent (paste into handoffs)
1. **Never end a turn with untracked work running.** Start long jobs with the Bash tool's `run_in_background: true`
   (the harness re-invokes you when the command exits), not `nohup … &`. If a job has to survive the session
   (nohup), also start a **Monitor** on a done-marker file or a log line, so the harness still wakes you.
2. **One driver script per handoff, with every job chained in it**: job 1 → job 2 → job 3 → summary. Run it as a
   single background command. Each step writes `build/<topic>/status.txt` (step, start time, done or failed), and the
   final step writes `build/<topic>/DONE` or `FAILED`. Steps that depend on an earlier result read it from a file,
   not from you. That way there are no gaps while waiting for a human or agent decision.
3. **Fail loudly and early.**
   - Each step checks its own outputs (expected files, row counts, no "Transient op", no "singular") before the next
     step starts.
   - On failure, the driver stops and writes `FAILED` with the log tail. Diagnose and retry at most twice, then write
     up and stop.
4. **Heartbeat fallback.** After launching, schedule a wakeup (**ScheduleWakeup**, or `/loop` in dynamic mode) at
   about 1.5× the estimated run time, at least 20 minutes. It only matters if a notification is missed.
5. **Report progress where the laptop can see it.**
   - Commit and push a one-line `STATUS` line at the top of the handoff (`> Running: step 2/4 since 01:10, ETA
     02:30`) at each step change.
   - At the end, push the `Done` line.
   - Send a **PushNotification** to Matt when the run finishes or fails, if that tool is available.
6. **Finish the whole brief in one go.** When the driver ends, continue straight on to the write-up, commit and push
   in the same session, without waiting to be asked.
7. **CPU budget via a queue.** Use `.claude/skills/mixed-signal-asic/scripts/sched.py`, or `xargs -P`, inside the
   driver, so one background command covers the whole batch.

## Laptop side (this session)
- After a handoff is started, watch GitHub for it with **ScheduleWakeup** (dynamic `/loop`), checking about every
  30 minutes: `git fetch` and look for the handoff's `Done` / `Running` line. When `Done` appears, pull and analyse
  without waiting for Matt.
- If Matt starts the pod agent with **Remote Control** enabled, it shows up in ListAgents. Then I can message it
  directly, for example to send a correction like the 10 fF update, instead of Matt pasting it.
- For a large multi-stage run that Matt opts into ("use a workflow"), a Workflow script can orchestrate the agents
  and report on completion.

## How to test it (next handoff)
- [ ] Is there a single driver script, started with `run_in_background`, and no bare `nohup`?
- [ ] Did the agent wake on its own when the driver finished, and go on to the write-up?
- [ ] Did a deliberately failing step (for example a missing file in a dry run) produce `FAILED` and a stop?
- [ ] Did the `Running` / `Done` lines reach GitHub, and did the laptop session pick up `Done` without a ping?
- [ ] Time from the last simulation ending to the push: target under 30 minutes, no human ping.

## Corner policy (added 2026-11-08)
Simulation time goes into dimensions that matter. In each handoff, list which corners each job uses, and why.
1. **The full set once per circuit change** (5 process corners × 0/70 °C, plus tt 27 °C): find which corner sets each
   limit (top of range, bottom of range, worst noise, worst fine/step).
2. **Iterate on those 3–4 bounding corners only.**
3. **The full set again only for sign-off.**

**VDD:** the current-fed ring moves −0.008 %/10 mV, so ±4.5 % VDD is about 0.1 % of f and stays out of maps and
sweeps. Keep one low-VDD spot check (3.15 V) at the worst corner, for headroom: is the DAC still saturated under vg,
and what is the swing? Revisit this if the topology changes.
