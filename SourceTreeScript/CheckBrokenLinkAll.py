from SourceTreeScript import handle_hrefs, get_article_list, scan_list
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

packSize = 50

output_mssg = queue.Queue()

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


def scan_techcontent():
    mdlist1 = glob.glob(tech_content_path + "articles/*.md")
    mdlist2 = glob.glob(tech_content_path + "articles/**/*.md")
    mdlist3 = glob.glob(tech_content_path + "develop/*.md")
    mdlist4 = glob.glob(tech_content_path + "develop/**/*.md")
    mdlist5 = glob.glob(tech_content_path + "downloads/*.md")
    mdlist6 = glob.glob(tech_content_path + "includes/*.md")
    folders = {}
    for filepath in mdlist2:
        directory, filename = os.path.split(filepath)
        if folders.get(directory) == None:
            folders[directory] = []
        folders[directory].append(filepath)
    threads = []
    output_mssgs = {}
    std_output=[]
    for key,value in folders.items():
        directory, foldername = os.path.split(key)
        if foldername in exist_folders:
            continue
        std_output.append(foldername+": "+str(len(value)))
        output_mssgs[foldername] = queue.Queue()
        scan_list(value, output_mssgs[foldername], threads, tech_content_path)


    if "others" not in exist_folders:
        std_output.append("others: "+str(len(mdlist1)))
        output_mssgs["others"] = queue.Queue()
        scan_list(mdlist1, output_mssgs["others"], threads, tech_content_path)

    if "develop" not in exist_folders:
        mdlist3.extend(mdlist4)
        std_output.append("develop: "+str(len(mdlist3)))
        output_mssgs["develop"] = queue.Queue()
        scan_list(mdlist3, output_mssgs["develop"], threads, tech_content_path)

    if "downloads" not in exist_folders:
        std_output.append("downloads: "+str(len(mdlist5)))
        output_mssgs["downloads"] = queue.Queue()
        scan_list(mdlist5, output_mssgs["downloads"], threads, tech_content_path)

    if "includes" not in exist_folders:
        std_output.append("includes: "+str(len(mdlist6)))
        output_mssgs["includes"] = queue.Queue()
        scan_list(mdlist6, output_mssgs["includes"], threads, tech_content_path)

    std_output.append(str(len(threads)))
    print("\n".join(std_output))

    for t in threads:
        while threading.active_count()>50:
            time.sleep(1)
        t.start()

    for t in threads:
        t.join()

    for folder, output_mssg in output_mssgs.items():
        links_output = open("./links_output/"+folder+".txt", "w", encoding="utf8")
        anchors_output = open("./anchors_output/"+folder+".txt", "w", encoding="utf8")
        links_out = ""
        anchors_out = ""
        while not output_mssg.empty():
            msg = output_mssg.get()+"\n"
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

def control_pro():
    threads = []
    for i in range(1,6):
        t = threading.Thread(target=sub_pro, args=[i])
        threads.append(t)
        t.start()

    t = threading.Thread(target=sub_pro, args=["left_nav"])
    threads.append(t)
    t.start()

    for t in threads:
        t.join()

    link_out_list = glob.glob("./links_output/*.txt")
    anchor_out_list = glob.glob("./anchors_output/*.txt")

    for filepath in link_out_list:
        if os.path.getsize(filepath)==0:
            os.remove(filepath)
    for filepath in anchor_out_list:
        if os.path.getsize(filepath)==0:
            os.remove(filepath)

    subprocess.call(["del", "links_output.zip"], shell=True)
    subprocess.call(["del", "anchors_output.zip"], shell=True)
    subprocess.call(["7z", "a", "-tzip", "links_output.zip", "./links_output/"], shell=True)
    subprocess.call(["7z", "a", "-tzip", "anchors_output.zip", "./anchors_output/"], shell=True)
    subprocess.call(["PowerShell", "-ExecutionPolicy", "ByPass", "-File", "./sendFile.ps1"], shell=True)

def sub_pro(index):
    subprocess.call([".\env\Scripts\python.exe",".\CheckBrokenLinkAll.py", str(index)], shell=True)

if __name__ == '__main__':
    if len(sys.argv) <= 1:
        control_pro()
    elif sys.argv[1] == "all":
        scan_techcontent()
    elif sys.argv[1] == "1":
        exist_folders = exist_folders1
        scan_techcontent()
    elif sys.argv[1] == "2":
        exist_folders = exist_folders2
        scan_techcontent()
    elif sys.argv[1] == "3":
        exist_folders = exist_folders3
        scan_techcontent()
    elif sys.argv[1] == "4":
        exist_folders = exist_folders4
        scan_techcontent()
    elif sys.argv[1] == "5":
        exist_folders = exist_folders5
        scan_techcontent()
    elif sys.argv[1] == "left_nav":
        scan_left_nav()