from SourceTreeScript import handle_hrefs, get_article_list, scan_list, scan_one
import sys
import glob
import os
import json
import threading
import subprocess
import queue
import math
import time
import re
from multiprocessing import Process, Queue

exist_folders = []

exist_folders1=["virtual-machines","hdinsight","mobile-services","app-service-mobile","develop","stream-analytics","event-hubs","virtual-machine-scale-sets","app-service-api","others","media-services","sql-data-warehouse","cloud-services","notification-hubs","vpn-gateway","cdn","multi-factor-authentication","automation","sql-server-stretch-database","resiliency","active-directory","app-service-web","virtual-network","iot-hub","azure-portal","site-recovery","application-gateway","redis-cache","batch","iot-suite","key-vault","sql-database","service-fabric","mysql","service-bus","documentdb","expressroute","load-balancer","traffic-manager","scheduler","downloads"]

exist_folders2=["includes","storage","backup","security","app-service","others","media-services","sql-data-warehouse","cloud-services","notification-hubs","vpn-gateway","cdn","multi-factor-authentication","automation","sql-server-stretch-database","resiliency","active-directory","app-service-web","virtual-network","iot-hub","azure-portal","site-recovery","application-gateway","redis-cache","batch","iot-suite","key-vault","sql-database","service-fabric","mysql","service-bus","documentdb","expressroute","load-balancer","traffic-manager","scheduler","downloads"]
#
exist_folders3=["includes","storage","backup","security","app-service","virtual-machines","hdinsight","mobile-services","app-service-mobile","develop","stream-analytics","event-hubs","virtual-machine-scale-sets","app-service-api","active-directory","app-service-web","virtual-network","iot-hub","azure-portal","site-recovery","application-gateway","redis-cache","batch","iot-suite","key-vault","sql-database","service-fabric","mysql","service-bus","documentdb","expressroute","load-balancer","traffic-manager","scheduler","downloads"]

exist_folders4=["includes","storage","backup","security","app-service","virtual-machines","hdinsight","mobile-services","app-service-mobile","develop","stream-analytics","event-hubs","virtual-machine-scale-sets","app-service-api","others","media-services","sql-data-warehouse","cloud-services","notification-hubs","vpn-gateway","cdn","multi-factor-authentication","automation","sql-server-stretch-database","resiliency","sql-database","service-fabric","mysql","service-bus","documentdb","expressroute","load-balancer","traffic-manager","scheduler","downloads"]
#
exist_folders5=["includes","storage","backup","security","app-service","virtual-machines","hdinsight","mobile-services","app-service-mobile","develop","stream-analytics","event-hubs","virtual-machine-scale-sets","app-service-api","others","media-services","sql-data-warehouse","cloud-services","notification-hubs","vpn-gateway","cdn","multi-factor-authentication","automation","sql-server-stretch-database","resiliency","active-directory","app-service-web","virtual-network","iot-hub","azure-portal","site-recovery","application-gateway","redis-cache","batch","iot-suite","key-vault"]

#exist_folders = ["application-gateway","app-service","app-service-api","app-service-web","azure-portal","cloud-services","event-hubs","expressroute","hdinsight","iot-hub","media-services","mobile-services","multi-factor-authentication","notification-hubs","redis-cache","resiliency","security","service-bus","service-fabric","sql-server-stretch-database","storage","stream-analytics","traffic-manager","virtual-machine-scale-sets","virtual-network","vpn-gateway", "includes", "others", "active-directory", "backup", "app-service-mobile", "iot-suite", "documentdb", "automation", "sql-data-warehouse", "sql-database", "load-balancer", "mysql", "scheduler", "site-recovery", "cdn", "batch", "develop", "downloads", "key-vault", "virtual-machines"]

tech_content_path = "E:/GitHub/techcontent/"

output_files = {}

packSize = 50

output_mssg = queue.Queue()

TERMINATED = "terminated"

def scan_left_nav():
    if len(sys.argv)>2:
        json_path = sys.argv[1]
        tech_content_path = sys.argv[2]
    else:
        json_path = "E:/vso/WACN/wacn_tech_landing_content/json/"
        tech_content_path = "E:/GitHub/techcontent/"
    jsonlist = glob.glob(json_path + "*.json")
    get_article_list(tech_content_path)
    all_message = queue.Queue()
    for filepath in jsonlist:
        filepath = filepath.replace("\\", "/")
        file = open(filepath, "r", encoding="utf8")
        content = file.read()
        file.close()
        json_object = json.loads(content)
        refs = []
        if "documentation,leftnav," not in filepath:
            for item in json_object:
                if item["link"] not in refs:
                    refs.append(item["link"])
        else:
            for navigation in json_object["navigation"]:
                for article in navigation["articles"]:
                    if article["link"] not in refs:
                        refs.append(article["link"])
        message = queue.Queue()
        handle_hrefs(refs, "", filepath, tech_content_path, message)
        if not message.empty():
            all_message.put("\n"+os.path.basename(filepath))
            while not message.empty():
                all_message.put(message.get())

    links_output = open("./links_output/left_nav.txt", "w", encoding="utf8")
    anchors_output = open("./anchors_output/left_nav.txt", "w", encoding="utf8")
    links_out = ""
    anchors_out = ""
    while not all_message.empty():
        msg = all_message.get()+"\n"
        if msg[:6]=="Broken":
            links_out+=msg
        elif msg[:6]=="Anchor":
            anchors_out+=msg
        else:
            links_out+=msg
            anchors_out+=msg
    links_out = re.sub("(^|\r?\n)(\r?\n.+\r?\n)+(\r?\n|$)",r"\1\3",links_out)
    anchors_out = re.sub("(^|\r?\n)(\r?\n.+\r?\n)+(\r?\n|$)",r"\1\3",anchors_out)
    links_output.write(links_out)
    anchors_output.write(anchors_out)
    links_output.close()
    anchors_output.close()

def sub_proc(input, output):
    line = input.get()
    output_mssg = queue.Queue()
    while line!= TERMINATED:
        scan_one(line, output_mssg, tech_content_path)
        out = ""
        while not output_mssg.empty():
            out += output_mssg.get()+"\n"
        output.put(out)
        line = input.get()

def control_proc(inputs, outputs, worker_num):
    #mdlist = list(glob.glob(tech_content_path + "articles/*.md"))
    mdlist = list(glob.glob(tech_content_path + "articles/*.md"))
    mdlist.extend(list(glob.glob(tech_content_path + "articles/**/*.md")))
    mdlist.extend(list(glob.glob(tech_content_path + "develop/*.md")))
    mdlist.extend(list(glob.glob(tech_content_path + "develop/**/*.md")))
    mdlist.extend(list(glob.glob(tech_content_path + "downloads/*.md")))
    mdlist.extend(list(glob.glob(tech_content_path + "includes/*.md")))

    file_queque = queue.Queue(len(mdlist))
    threads = []
    distr(file_queque, mdlist)
    for i in range(worker_num):
        t = threading.Thread(target=worker, args=[file_queque, inputs[i], outputs[i], i])
        threads.append(t)
        t.start()
    link_out_list = glob.glob("./links_output/*.txt")
    anchor_out_list = glob.glob("./anchors_output/*.txt")

    for filepath in link_out_list:
        os.remove(filepath)
    for filepath in anchor_out_list:
        os.remove(filepath)
    scan_left_nav()
    for t in threads:
        t.join()

    for folder, output_str in output_files.items():

        links_out = output_str[0]
        anchors_out = output_str[1]
        links_out_list = re.findall("(.+\r?\n(.+\r?\n)+)",links_out)
        links_out = ""
        for i in links_out_list:
            links_out += "\n"+i[0]
        anchors_out_list = re.findall("(.+\r?\n(.+\r?\n)+)",anchors_out)
        anchors_out = ""
        for i in anchors_out_list:
            anchors_out += "\n"+i[0]

        if links_out.strip()!="":
            links_output = open("./links_output/"+folder+".txt", "w", encoding="utf8")
            links_output.write(links_out)
            links_output.close()
        if anchors_out!="":
            anchors_output = open("./anchors_output/"+folder+".txt", "w", encoding="utf8")
            anchors_output.write(anchors_out)
            anchors_output.close()

    os.remove("./links_output.zip")
    os.remove("./anchors_output.zip")
    subprocess.call(["7z", "a", "-tzip", "links_output.zip", "./links_output/"], shell=True)
    subprocess.call(["7z", "a", "-tzip", "anchors_output.zip", "./anchors_output/"], shell=True)
    subprocess.call(["PowerShell", "-ExecutionPolicy", "ByPass", "-File", "./sendFile.ps1"], shell=True)

def worker(file_queque, input, output, i):
    while not file_queque.empty():
        filepath = file_queque.get().replace("\\","/")
        output.put(filepath)
        line = input.get()
        print(str(i)+": " + filepath)
        if line!="":
            m = re.match("\n(\w+)/([^/]+)/(.+)\.md\n.+",line)
            if m:
                ma = m.groups()
                if ma[0]=="articles":
                    if not output_files.get(ma[1]):
                        output_files[ma[1]] = ["", ""]
                    out_file = output_files[ma[1]]
                else:
                    if not output_files.get("develop"):
                        output_files["develop"] = ["", ""]
                    out_file = output_files["develop"]
            else:
                m = re.match("\n(\w+)/(.+)\.md\n.+",line)
                ma = m.groups()
                if ma[0]=="articles":
                    if not output_files.get("others"):
                        output_files["others"] = ["", ""]
                    out_file = output_files["others"]
                else:
                    if not output_files.get(ma[0]):
                        output_files[ma[0]] = ["", ""]
                    out_file = output_files[ma[0]]
            for msg in line.split("\n"):
                if len(msg)<6:
                    out_file[0]+=msg+"\n"
                    out_file[1]+=msg+"\n"
                elif msg[:6]=="Broken":
                    out_file[0]+=msg+"\n"
                elif msg[:6]=="Anchor":
                    out_file[1]+=msg+"\n"
                else:
                    out_file[0]+=msg+"\n"
                    out_file[1]+=msg+"\n"
            print("start:\n"+line+"end\n")
    output.put(TERMINATED)
    print("Proccess "+str(i)+" ended")
    return

def distr(file_queque, mdlist):
    for filepath in mdlist:
        file_queque.put(filepath)

if __name__ == '__main__':
    inputs = []
    outputs = []
    worker_num = 50
    ps = []
    for i in range(worker_num):
        r1 = Queue()
        r2 = Queue()
        p = Process(target=sub_proc, args=[r1, r2])
        ps.append(p)
        inputs.append(r2)
        outputs.append(r1)
    p = Process(target=control_proc, args=[inputs, outputs, worker_num])
    ps.append(p)

    for p in ps:
        p.start()
    for p in ps:
        p.join()