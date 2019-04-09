from crontab import CronTab

cron = CronTab(user=True)

job = cron.new(command="python /main.py")

job.minute.every(5)

job.enable()

print(job.is_valid())
