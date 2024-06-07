import json
import subprocess

def f_get_zpool_status():
  result = subprocess.run(['zpool', 'list', '-v'], stdout=subprocess.PIPE)
  data = result.stdout.decode('utf-8')
  lines = data.split("\n")
  json_data = []
  current_pool = None
  current_config = None

  for line in lines[1:]:
      if not line.strip():
          continue
      if not line.startswith("  "):
          if current_pool:
              if current_config:
                  current_pool["config"].append(current_config)
              json_data.append(current_pool)
          current_pool = {"name": line.split()[0], "status": line.split()[-2], "config": []}
          current_config = None
      elif line.startswith("    "):
          if current_config:
              current_config["config"].append({"name": line.strip().split()[0], "status": line.strip().split()[-1]})
      else:
          if current_config:
              current_pool["config"].append(current_config)
          current_config = {"name": line.strip().split()[0], "status": line.strip().split()[-1], "config": []}

  if current_config:
      current_pool["config"].append(current_config)
  if current_pool:
      json_data.append(current_pool)

  print(json.dumps(json_data, indent=4))

f_get_zpool_status()
