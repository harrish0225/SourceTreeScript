import glob
import os

landingpages = {
    "/documentation/services/active-directory-b2c/":"/articles/active-directory-b2c/index.md",
    "/documentation/services/active-directory-domain-services/":"/articles/active-directory-domain-services/index.md",
    "/documentation/services/active-directory-ds/":"/articles/active-directory-ds/index.md",
    "/documentation/services/advisor/":"/articles/advisor/index.md",
    "/documentation/services/analysis-services/":"/articles/analysis-services/index.md",
    "/documentation/services/api-management/":"/articles/api-management/index.md",
    "/documentation/services/application-gateway/":"/articles/application-gateway/index.md",
    "/documentation/services/application-insights/":"/articles/application-insights/index.md",
    "/documentation/services/app-service/api/":"/articles/app-service-api/index.md",
    "/documentation/services/app-service/logic/":"/articles/app-service-logic/index.md",
    "/documentation/services/app-service/mobile/":"/articles/app-service-mobile/index.md",
    "/documentation/services/app-service/web/":"/articles/app-service-web/index.md",
    "/documentation/services/app-service/":"/articles/app-service/index.md",
    "/documentation/services/automation/":"/articles/automation/index.md",
    "/documentation/services/azure-functions/":"/articles/azure-functions/index.md",
    "/documentation/services/azure-government/":"/articles/azure-government/index.md",
    "/documentation/services/azure-portal/":"/articles/azure-portal/index.md",
    "/documentation/services/azure-resource-manager/":"/articles/azure-resource-manager/index.md",
    "/documentation/services/azure-stack/":"/articles/azure-stack/index.md",
    "/documentation/services/azure-supportability/":"/articles/azure-supportability/index.md",
    "/documentation/services/azure-operations-guide/":"/articles/azure-operations-guide/index.md",
    "/documentation/services/backup/":"/articles/backup/index.md",
    "/documentation/services/batch/":"/articles/batch/index.md",
    "/documentation/services/billing/":"/articles/billing/index.md",
    "/documentation/services/biztalk-services/":"/articles/biztalk-services/index.md",
    "/documentation/services/cache/":"/articles/cache/index.md",
    "/documentation/services/cdn/":"/articles/cdn/index.md",
    "/documentation/services/cloud-services/":"/articles/cloud-services/index.md",
    "/documentation/services/cognitive-services/":"/articles/cognitive-services/index.md",
    "/documentation/services/connectors/":"/articles/connectors/index.md",
    "/documentation/services/container-registry/":"/articles/container-registry/index.md",
    "/documentation/services/container-service/":"/articles/container-service/index.md",
    "/documentation/services/data-catalog/":"/articles/data-catalog/index.md",
    "/documentation/services/data-factory/":"/articles/data-factory/index.md",
    "/documentation/services/data-lake-analytics/":"/articles/data-lake-analytics/index.md",
    "/documentation/services/data-lake-store/":"/articles/data-lake-store/index.md",
    "/documentation/services/devtest-lab/":"/articles/devtest-lab/index.md",
    "/documentation/services/dns/":"/articles/dns/index.md",
    "/documentation/services/documentdb/":"/articles/documentdb/index.md",
    "/documentation/services/event-hubs/":"/articles/event-hubs/index.md",
    "/documentation/services/expressroute/":"/articles/expressroute/index.md",
    "/documentation/services/functions/":"/articles/functions/index.md",
    "/documentation/services/guidance/":"/articles/guidance/index.md",
    "/documentation/services/hdinsight/":"/articles/hdinsight/index.md",
    "/documentation/services/identity/":"/articles/active-directory/index.md",
    "/documentation/services/iot-hub/":"/articles/iot-hub/index.md",
    "/documentation/services/iot-suite/":"/articles/iot-suite/index.md",
    "/documentation/services/key-vault/":"/articles/key-vault/index.md",
    "/documentation/services/load-balancer/":"/articles/load-balancer/index.md",
    "/documentation/services/log-analytics/":"/articles/log-analytics/index.md",
    "/documentation/services/logic-apps/":"/articles/logic-apps/index.md",
    "/documentation/services/machine-learning/":"/articles/machine-learning/index.md",
    "/documentation/services/marketplace-consumer/":"/articles/marketplace-consumer/index.md",
    "/documentation/services/marketplace-publishing/":"/articles/marketplace-publishing/index.md",
    "/documentation/services/media-services/":"/articles/media-services/index.md",
    "/documentation/services/mobile-services/":"/articles/mobile-services/index.md",
    "/documentation/services/monitoring-and-diagnostics/":"/articles/monitoring-and-diagnostics/index.md",
    "/documentation/services/multi-factor-authentication/":"/articles/multi-factor-authentication/index.md",
    "/documentation/services/mysql/":"/articles/mysql/index.md",
    "/documentation/services/networking/":"/articles/virtual-network/index.md",
    "/documentation/services/notification-hubs/":"/articles/notification-hubs/index.md",
    "/documentation/services/operations-management-suite/":"/articles/operations-management-suite/index.md",
    "/documentation/services/power-bi-embedded/":"/articles/power-bi-embedded/index.md",
    "/documentation/services/redis-cache/":"/articles/redis-cache/index.md",
    "/documentation/services/remoteapp/":"/articles/remoteapp/index.md",
    "/documentation/services/resiliency/":"/articles/resiliency/index.md",
    "/documentation/services/resource-health/":"/articles/resource-health/index.md",
    "/documentation/services/scheduler/":"/articles/scheduler/index.md",
    "/documentation/services/search/":"/articles/search/index.md",
    "/documentation/services/security/":"/articles/security/index.md",
    "/documentation/services/security-center/":"/articles/security-center/index.md",
    "/documentation/services/service-bus/":"/articles/service-bus/index.md",
    "/documentation/services/service-bus-messaging/":"/articles/service-bus-messaging/index.md",
    "/documentation/services/service-bus-relay/":"/articles/service-bus-relay/index.md",
    "/documentation/services/service-fabric/":"/articles/service-fabric/index.md",
    "/documentation/services/site-recovery/":"/articles/site-recovery/index.md",
    "/documentation/services/sql-databases/":"/articles/sql-database/index.md",
    "/documentation/services/sql-data-warehouse/":"/articles/sql-data-warehouse/index.md",
    "/documentation/services/sql-server-stretch-database/":"/articles/sql-server-stretch-database/index.md",
    "/documentation/services/storage/":"/articles/storage/index.md",
    "/documentation/services/storsimple/":"/articles/storsimple/index.md",
    "/documentation/services/stream-analytics/":"/articles/stream-analytics/index.md",
    "/documentation/services/traffic-manager/":"/articles/traffic-manager/index.md",
    "/documentation/services/virtual-machines/":"/articles/virtual-machines/index.md",
    "/documentation/services/virtual-machines/linux/":"/articles/virtual-machines/linux/index.md",
    "/documentation/services/virtual-machines/windows/":"/articles/virtual-machines/windows/index.md",
    "/documentation/services/virtual-machine-scale-sets/":"/articles/virtual-machine-scale-sets/index.md",
    "/documentation/services/vpn-gateway/":"/articles/vpn-gateway/index.md",
    "/documentation/services/web-sites/":"/articles/app-service-web/index.md"
    }

all_articles_path = {}

def get_all_articles_path(repopath):
    mdList = glob.glob(repopath+"/articles/**/*.md")
    mdList.extend(glob.glob(repopath+"/articles/*.md"))
    mdList.extend(glob.glob(repopath+"/articles/**/**/*.md"))
    mdList.extend(glob.glob(repopath+"/articles/**/**/**/*.md"))
    for path in mdList:
        path = path.replace("\\", "/")
        filepath, filename = os.path.split(path)
        if all_articles_path.get(filename)!=None:
            print("error: duplicate files: "+path+" and "+all_articles_path[filename])
            exit(-1)
        all_articles_path[filename] = path
