import subprocess

p = subprocess.Popen(["python", "manage.py", "makemigrations"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
out, err = p.communicate(input="y\n"*50)
print("STDOUT:")
print(out)
print("STDERR:")
print(err)
