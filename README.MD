# install dependencies

PYTHON version == 3.12

```bash
pip install -r req.txt
```

**⚠️ IMPORTANT**

- **Each cell MUST be RUN ONCE Denoted by 🔴** or you'll accidentally queue duplicate jobs.
- **Other cells can be RUN to check status and download results Denoted by 🟢**
- The first run will return a **job_id** for each batch – **don’t mix them up** or subsequent cells won’t work.
- Uncomment each invocation **one at a time**, and **run it**.
- After running, **copy the generated job_id** into the class variable below, then move on to the next cell.
- **DO NOT** run the next cell until **all previous jobs** have completed.
- Each batch can take ~24 h. You may shut down and come back: to check status, use the job_id you saved.

# First run: invoke and capture job_id

```python
# obj.invoke_job()
```

# ➡️ After running, copy the printed job_id here:

```python
# obj.job_id = "PASTE_FIRST_GENERATED_JOB_ID_HERE"
```

**Check status of your CharGen job**
Uses the job_id you just set
Run this cell anytime to see if it’s done
DO NOT proceed until status == "succeeded" or final failure

```python
status = client.batches.get(obj.job_id)
print(f"Job {obj.job_id} status: {status.status}")
```

**Check all Batch jobs**

```python
jobs = client.batches.list()
len(jobs.data)
jobs.data
```
