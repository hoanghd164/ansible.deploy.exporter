import requests, subprocess, math, time, yaml, socket
from requests.auth import HTTPBasicAuth
from prometheus_client import Gauge, start_http_server
from urllib.parse import urlparse
import subprocess
import json
import sys

# curl -i -u admin:password http://10.237.7.81:15672/api/queues

count = 0
time_start = time.time()
get_hostname = socket.gethostname()

with open('config.yml', 'r') as file:
    config = yaml.safe_load(file)

exporter_port = config['default']['exporter_port']
check_interval = config['default']['check_interval']

# Convert to the desired format
rabbitmq_urls = []
for worker, details in config["sensor"]["rabbitmq"]['targets'].items():
    url = f"http://{details['ip']}:{details['port']}"
    rabbitmq_urls.append({worker: [url, details['user'], details['password']]})

def convert_size(size_bytes):
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"

class c_process:
    def __init__(self):
        self.TOTAL_PROCESS = Gauge('total_process', 'Total Process')
        self.PROCESS_DETAILS = Gauge('process_details', 'Process Details', ['name', 'pid', 'cpu', 'mem', 'vsz', 'rss', 'tty', 'stat', 'start', 'time', 'command'])

    def f_get_process(self, process_name):
        output = subprocess.check_output(f"ps -aux | grep {process_name}", shell=True)
        lines = output.decode().split('\n')
        data = []
        for line in lines:
            if line and f"grep {process_name}" not in line:
                fields = line.split()
                data.append({
                    'USER': fields[0],
                    'PID': fields[1],
                    'CPU': fields[2],
                    'MEM': fields[3],
                    'VSZ': fields[4],
                    'RSS': fields[5],
                    'TTY': fields[6],
                    'STAT': fields[7],
                    'START': fields[8],
                    'TIME': fields[9],
                    'COMMAND': ' '.join(fields[10:]),
                })

        self.TOTAL_PROCESS.set(len(data))
        for item in data:
            self.PROCESS_DETAILS.labels(
                name=item['USER'],
                pid=item['PID'],
                cpu=item['CPU'],
                mem=item['MEM'],
                vsz=item['VSZ'],
                rss=item['RSS'],
                tty=item['TTY'],
                stat=item['STAT'],
                start=item['START'],
                time=item['TIME'],
                command=item['COMMAND']
            ).set(1)

class c_rabbitmq:
    def __init__(self):
        self.RABBITMQ_TOTAL_QUEUE = Gauge('rabbitmq_total_queue', 'Rabbitmq Total Queue',['rabbitmq_host'])
        self.RABBITQM_TOTAL_MESSAGES = Gauge('rabbitmq_total_messages', 'Rabbitmq Total Messages', ['rabbitmq_host'])
        self.RABBITQM_DETAILS_QUEUE = Gauge('rabbitmq_details_queue', 'Rabbitmq Details Queue', ['rabbitmq_host', 'name'])

    def f_get_json_from_api(rabbitmq_url, username, password):
        url = f"{rabbitmq_url}/api/queues"
        response = requests.get(url, auth=HTTPBasicAuth(username, password))
        return response.json()

    def f_send_alerts_when_queue_is_finish(self, url):
        list_queue = []
        results = c_rabbitmq.f_get_json_from_api(list(url.values())[0][0], list(url.values())[0][1], list(url.values())[0][2])

        for key, value in url.items():
            full_url = value[0]
            parsed_url = urlparse(full_url)
            ip_only = parsed_url.hostname

        # self.RABBITMQ_TOTAL_QUEUE.set(len(results))
        self.RABBITMQ_TOTAL_QUEUE.labels(rabbitmq_host=ip_only).set(len(results))

        for result in results:
            list_queue.append(result['messages'])
            # self.RABBITQM_DETAILS_QUEUE.labels(name=result['name']).set((result['messages']))
            self.RABBITQM_DETAILS_QUEUE.labels(name=result['name'], rabbitmq_host=ip_only).set((result['messages']))

        total_messages = sum(list_queue)
        # self.RABBITQM_TOTAL_MESSAGES.set(total_messages)
        self.RABBITQM_TOTAL_MESSAGES.labels(rabbitmq_host=ip_only).set(total_messages)

class c_zfs:
    def __init__(self):
        self.ZPOOL_CAPACITY = Gauge('zpool_capacity', 'Zpool Capacity', ['name', 'hostname'])
        self.ZPOOL_AVAIL = Gauge('zpool_avail', 'Zpool Avail', ['name', 'hostname'])
        self.ZPOOL_SIZE = Gauge('zpool_size', 'Zpool Size', ['name', 'hostname'])
        self.ZPOOL_STATUS = Gauge('zpool_status', 'Zpool Status', ['name', 'hostname'])

        self.ZFS_CAPACITY = Gauge('zfs_capacity', 'Zfs Capacity', ['name', 'mountpoint', 'hostname'])
        self.ZFS_USED = Gauge('zfs_used', 'Zfs Used', ['name', 'mountpoint', 'hostname'])
        self.ZFS_AVAIL = Gauge('zfs_avail', 'Zfs Avail', ['name', 'mountpoint', 'hostname'])
        self.ZFS_TOTAL = Gauge('zfs_total', 'Zfs Total', ['name', 'mountpoint', 'hostname'])
        self.ZFS_REFRES = Gauge('zfs_refres', 'Zfs Refres', ['name', 'mountpoint', 'hostname'])

        self.ZPOOL_MEMBER_STATUS = Gauge('zpool_member_status', 'Zpool Member Status', ['name', 'member', 'hostname'])

        # Initialize the new attributes
        self.ZPOOL_READ_OPS = Gauge('zpool_read_ops', 'Zpool Read Operations', ['name', 'member', 'hostname'])
        self.ZPOOL_WRITE_OPS = Gauge('zpool_write_ops', 'Zpool Write Operations', ['name', 'member', 'hostname'])
        self.ZPOOL_READ_BW = Gauge('zpool_read_bw', 'Zpool Read Bandwidth', ['name', 'member', 'hostname'])
        self.ZPOOL_WRITE_BW = Gauge('zpool_write_bw', 'Zpool Write Bandwidth', ['name', 'member', 'hostname'])

    def is_number(s):
        try:
            float(s)
            return True
        except ValueError:
            return False

    # @staticmethod
    # def convert_to_float(s):
    #     multipliers = {'K': 1e3, 'M': 1e6, 'G': 1e9, 'T': 1e12}

    #     if s[-1] in multipliers:
    #         return float(s[:-1]) * multipliers[s[-1]]
    #     else:
    #         return float(s)


    @staticmethod
    def convert_to_float(s):
        multipliers = {'K': 1e3, 'M': 1e6, 'G': 1e9, 'T': 1e12}

        if s == '-':
            return 0.0
        elif s[-1] in multipliers:
            return float(s[:-1]) * multipliers[s[-1]]
        else:
            return float(s)

    def f_get_zpool_size():
        result = subprocess.run(['zpool', 'list', '-p'], capture_output=True, text=True)
        lines = result.stdout.split('\n')
        header = lines[0].split()
        data = []
        for line in lines[1:]:
            if line:
                values = line.split()
                data.append(dict(zip(header, values)))
        return data
    
    def f_send_alerts_when_zpool_is_full(self):
        results = c_zfs.f_get_zpool_size()
        for result in results:
            pool_capacity = int(result['CAP'])

            self.ZPOOL_CAPACITY.labels(name=result['NAME'], hostname=get_hostname).set(pool_capacity)
            self.ZPOOL_AVAIL.labels(name=result['NAME'], hostname=get_hostname).set(int(result['FREE']))
            self.ZPOOL_SIZE.labels(name=result['NAME'], hostname=get_hostname).set(int(result['SIZE']))
            self.ZPOOL_STATUS.labels(name=result['NAME'], hostname=get_hostname).set(1 if result['HEALTH'] == 'ONLINE' else 0)

    def f_get_zfs_size():
        result = subprocess.run(['zfs', 'list', '-p'], capture_output=True, text=True)
        lines = result.stdout.split('\n')
        header = lines[0].split()
        data = []
        for line in lines[1:]:
            if line:
                values = line.split()
                data.append(dict(zip(header, values)))
        return data
    
    def f_send_alerts_when_zfs_is_full(self):
        results = c_zfs.f_get_zfs_size()
        for result in results:
            zfs_used = int(result['USED'])
            zfs_avail = int(result['AVAIL'])
            zfs_refres = int(result['REFER'])
            zfs_mountpoint = result['MOUNTPOINT']
            zfs_total = zfs_used + zfs_avail
            zfs_percent = round((zfs_used / zfs_total) * 100)

            self.ZFS_CAPACITY.labels(name=result['NAME'], mountpoint=zfs_mountpoint, hostname=get_hostname).set(zfs_percent)
            self.ZFS_USED.labels(name=result['NAME'], mountpoint=zfs_mountpoint, hostname=get_hostname).set(zfs_used)
            self.ZFS_AVAIL.labels(name=result['NAME'], mountpoint=zfs_mountpoint, hostname=get_hostname).set(zfs_avail)
            self.ZFS_TOTAL.labels(name=result['NAME'], mountpoint=zfs_mountpoint, hostname=get_hostname).set(zfs_total)
            self.ZFS_REFRES.labels(name=result['NAME'], mountpoint=zfs_mountpoint, hostname=get_hostname).set(zfs_refres)

    def f_get_zpool_status_old(self):
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

    def f_get_zpool_status(self):
        result = subprocess.run(['zpool', 'list', '-v'], stdout=subprocess.PIPE)
        data = result.stdout.decode('utf-8')

        lines = data.split("\n")
        header = lines[0].split()
        json_data = []
        current_pool = None
        current_member = None

        for line in lines[1:]:
            if not line.strip():
                continue
            if not line.startswith("  "):
                if current_pool:
                    if current_member:
                        current_pool["members"].append(current_member)
                    json_data.append(current_pool)
                current_pool = {"name": line.split()[0], "status": line.split()[-2], "members": []}
                current_member = None
            else:
                if current_member:
                    current_pool["members"].append(current_member)
                current_member = {"name": line.strip().split()[0], "status": line.strip().split()[-1]}

        if current_member:
            current_pool["members"].append(current_member)
        if current_pool:
            json_data.append(current_pool)

        for pool in json_data:
            self.ZPOOL_MEMBER_STATUS.labels(name=pool['name'], member='pool', hostname=get_hostname).set(1 if pool['status'] == 'ONLINE' else 0)
            for member in pool["members"]:
                self.ZPOOL_MEMBER_STATUS.labels(name=pool['name'], member=member['name'], hostname=get_hostname).set(1 if member['status'] == 'ONLINE' else 0)

    def f_get_zpool_iops(self):
        result = subprocess.run(['timeout', '2', 'zpool', 'iostat', '-v', '1'], stdout=subprocess.PIPE)
        split_data =  result.stdout.decode('utf-8').split("-----------  -----  -----  -----  -----  -----  -----")
        last_three_elements = split_data[-3:]
        add_on = '''              capacity     operations     bandwidth 
pool        alloc   free   read  write   read  write'''

        if 'capacity' not in last_three_elements[0]:
            last_three_elements = [add_on] + last_three_elements 
        data = ''.join(last_three_elements)
        print(data)

        lines = data.split("\n")
        json_data = []
        current_pool = None
        current_member = None

        for line in lines[2:]:
            if not line.strip():
                continue
            if not line.startswith("  "):
                if current_pool:
                    if current_member:
                        current_pool["members"].append(current_member)
                    json_data.append(current_pool)
                current_pool = {"name": line.split()[0], "read_ops": line.split()[3], "write_ops": line.split()[4], "read_bw": line.split()[5], "write_bw": line.split()[6], "members": []}
                current_member = None
            else:
                if current_member:
                    current_pool["members"].append(current_member)
                current_member = {"name": line.strip().split()[0], "read_ops": line.strip().split()[3], "write_ops": line.strip().split()[4], "read_bw": line.strip().split()[5], "write_bw": line.strip().split()[6]}
                print(current_member)
        if current_member:
            current_pool["members"].append(current_member)
        if current_pool:
            json_data.append(current_pool)

        for pool in json_data:
            if pool['members']:
                read_ops = (pool['read_ops'])
                write_ops = (pool['write_ops'])
                print(f"Device: {pool['name']} Read Ops: {read_ops}")
                print(f"Device: {pool['name']} Write Ops: {write_ops}")
                self.ZPOOL_READ_OPS.labels(name=pool['name'], member='pool', hostname=get_hostname).set(read_ops)
                self.ZPOOL_WRITE_OPS.labels(name=pool['name'], member='pool', hostname=get_hostname).set(c_zfs.convert_to_float(pool['write_ops']))
                self.ZPOOL_READ_BW.labels(name=pool['name'], member='pool', hostname=get_hostname).set(c_zfs.convert_to_float(pool['read_bw']))
                self.ZPOOL_WRITE_BW.labels(name=pool['name'], member='pool', hostname=get_hostname).set(c_zfs.convert_to_float(pool['write_bw']))
                for member in pool["members"]:
                    self.ZPOOL_READ_OPS.labels(name=pool['name'], member=member['name'], hostname=get_hostname).set(c_zfs.convert_to_float(member['read_ops']))
                    self.ZPOOL_WRITE_OPS.labels(name=pool['name'], member=member['name'], hostname=get_hostname).set(c_zfs.convert_to_float(member['write_ops']))
                    self.ZPOOL_READ_BW.labels(name=pool['name'], member=member['name'], hostname=get_hostname).set(c_zfs.convert_to_float(member['read_bw']))
                    self.ZPOOL_WRITE_BW.labels(name=pool['name'], member=member['name'], hostname=get_hostname).set(c_zfs.convert_to_float(member['write_bw']))

if __name__ == '__main__':
    # Start up the server to expose the metrics.
    start_http_server(exporter_port)
    rabbitmq_instance = c_rabbitmq()
    iprocess_instance = c_process()
    zfs_instance = c_zfs()
    
    # Loop to keep the script running
    while True:
        iprocess_instance.f_get_process('/usr/bin/rbd')
        if config['sensor']['zfs']['enabled'] == True:
            zfs_instance.f_send_alerts_when_zpool_is_full()
            zfs_instance.f_send_alerts_when_zfs_is_full()
            zfs_instance.f_get_zpool_status()
            zfs_instance.f_get_zpool_iops()

        if config['sensor']['rabbitmq']['enabled'] == True:
            for url in rabbitmq_urls:
                rabbitmq_instance.f_send_alerts_when_queue_is_finish(url)

        # To keep the script running
        time_end = time.time()
        count += 1
        print(f"-> Finished {count} times in {time_end - time_start} seconds")
        time.sleep(check_interval)