import docker
import os
import tarfile
import zipfile
import shutil
import argparse
import xml.etree.ElementTree as ET
import csv
import codecs

# 一次性打包整个根目录
def make_targz(output_filename, source_dir):
    with tarfile.open(output_filename, "w:gz") as tar:
        tar.add(source_dir, arcname=os.path.basename(source_dir))

# 解压tar
def un_tar(file_name):
    tar = tarfile.open(file_name)
    names = tar.getnames()

    # 由于解压后是许多文件，预先建立同名文件夹
    if os.path.isdir(names[0]):
        pass
    else:
        os.mkdir(names[0])

    begin = (names[0] + "/io.cloudbeaver.resources.drivers.base_", names[0] + "/org.jkiss.dbeaver.ext.generic_")
    for name in names:
        if name.startswith(begin):
            tar.extract(name)

    tar.close()
    os.remove(file_name)

# 压缩jar包
def make_jar(path, target):
    startdir = path  # 要压缩的文件夹路径
    file_news = target  # 压缩后文件夹的名字
    z = zipfile.ZipFile(file_news, 'w', zipfile.ZIP_DEFLATED)  # 参数一：文件夹名
    for dirpath, dirnames, filenames in os.walk(startdir):  # os.walk 遍历目录
        fpath = dirpath.replace(startdir, '')  # 这一句很重要，不replace的话，就从根目录开始复制
        fpath = fpath and fpath + os.sep or ''  # os.sep路径分隔符
        for filename in filenames:
            z.write(os.path.join(dirpath, filename), fpath + filename)
            # os.path.join()函数用于路径拼接文件路径。
            # os.path.split(path)把path分为目录和文件两个部分，以列表返回
    z.close()

# 修改配置文件，添加驱动信息
def changePlugins(dbeaverPlugin, cloudbeaverPlugin, driversCSV):
    dbeaverDrivers = ""
    resourcesExtension = ""
    bundlesExtension = ""
    driversExtension = ""

    dbeaver = ET.parse(dbeaverPlugin)
    dbeaverRoot = dbeaver.getroot()
    driversList = dbeaverRoot.iter("drivers")
    if driversList is not None:
        for drivers in driversList:
            if drivers.find("driver") is not None:
                dbeaverDrivers = drivers

    cloudBeaver = ET.parse(cloudbeaverPlugin)
    cloudBeaverRoot = cloudBeaver.getroot()
    extensionList = cloudBeaverRoot.iter("extension")
    if extensionList is not None:
        for extension in extensionList:
            if extension.attrib.get('point') == "org.jkiss.dbeaver.resources":
                resourcesExtension = extension
            elif extension.attrib.get('point') == "org.jkiss.dbeaver.product.bundles":
                bundlesExtension = extension
            elif extension.attrib.get('point') == "io.cloudbeaver.driver":
                driversExtension = extension

    with codecs.open(driversCSV, encoding='utf-8') as driversPlugins:
        for driverPlugin in csv.DictReader(driversPlugins, skipinitialspace=True):
            # 插入内容至dbeaver-plugin.xml
            fileContent = {
                "type": "jar",
                "path": "drivers/" + driverPlugin.get('id'),
                "bundle": "drivers." + driverPlugin.get('id')
            }
            driverContent = {
                "id": driverPlugin.get('id'),
                "label": driverPlugin.get('label'),
                "icon": driverPlugin.get('icon'),
                "iconBig": driverPlugin.get('icon'),
                "class": driverPlugin.get('class'),
                "sampleURL": driverPlugin.get('sampleURL'),
                "defaultPort": driverPlugin.get('defaultPort'),
                "webURL": "",
                "description": driverPlugin.get('description')
            }
            file = ET.Element("file", fileContent)
            newDriver = ET.Element("driver", driverContent)
            newDriver.append(file)
            dbeaverDrivers.append(newDriver)

            # 插入内容至cloudbeaver-plugin.xml
            resourcesExtension.append(ET.Element("resource", {"name": "drivers/" + driverPlugin.get('id')}))
            bundlesExtension.append(ET.Element("bundle", {"id": "drivers." + driverPlugin.get('id'),
                                                          "label": driverPlugin.get('label')}))
            driversExtension.append(ET.Element("driver", {"id": "generic:" + driverPlugin.get('id')}))

            print("成功扩展：" + driverPlugin.get('label'))

    dbeaver.write(dbeaverPlugin, encoding="utf-8", xml_declaration=True)
    cloudBeaver.write(cloudbeaverPlugin, encoding="utf-8", xml_declaration=True)

if __name__ == '__main__':
    client = docker.from_env()  # 创建一个docker客户端

    # 关闭正在运行的cloudbeaver容器
    try:
        oldContainer = client.containers.get("cloudbeaver")
        oldContainer.kill()
        oldContainer.remove()
    except:
        pass

    # 传递脚本参数是否下载最新镜像
    parser = argparse.ArgumentParser(description='脚本传参')
    parser.add_argument('--pull', '-p', type=str, default="false", required=False, help="download the latest image")
    args = parser.parse_args()
    pull = args.pull+""
    if pull == "true" or pull == "t":
        try:
            oldImage = client.images.get("dbeaver/cloudbeaver:latest")
            oldImage.remove()
        except:
            pass

        try:
            print("正在拉取最新镜像")
            client.images.pull("dbeaver/cloudbeaver:latest")
            print("最新镜像拉取完毕")
        except:
            raise Exception("最新镜像拉取失败")
    else:
        pass

    # 运行镜像前先判断是否有
    try:
        cloudbeaverImage = client.images.get("dbeaver/cloudbeaver:latest")
    except:
        raise Exception("未找到cloudbeaver镜像")

    # 运行新的cloudbeaver镜像
    container = client.containers.run("dbeaver/cloudbeaver:latest",  # image_name 是我们docker镜像的name, REPOSITORY:TAG
                                      name="cloudbeaver",  # 容器name
                                      detach=True,  # detach=True,是docker run -d 后台运行容器
                                      remove=True,  # 容器如果stop了，会自动删除容器
                                      stdin_open=True,  # 保持stdin打开即使没有attach到容器内部，相当于docker run -i
                                      tty=True,  # 分配一个tty  docker run -t
                                      ports={8978: 8978},
                                      # Maps CloudBeaver public port (8978) to the host machine port (8978)
                                      volumes=["/var/cloudbeaver/workspace:/opt/cloudbeaver/workspace"],
                                      # 与宿主机的共享目录， docker run -v /var/:/opt
                                      command="/bin/bash")  # The command to run in the container

    # 上传驱动文件
    make_targz('drivers.tar', "./drivers")
    driverFile = open('drivers.tar', 'rb')
    ok = container.put_archive(path='/opt/cloudbeaver', data=driverFile)
    if not ok:
        raise Exception('上传驱动文件失败')
    driverFile.close()
    os.remove('drivers.tar')

    # 下载jar包
    plugins = open('plugins.tar', 'wb')
    try:
        bits, stat = container.get_archive('/opt/cloudbeaver/server/plugins/')
        for chunk in bits:
            plugins.write(chunk)
        plugins.close()
    except:
        raise Exception("下载jar包失败")

    # 修改配置文件
    un_tar("plugins.tar")
    jars = os.listdir("./plugins")

    cloudbeaverJarName = ""
    dbeaverJarName = ""
    for jar in jars:
        if jar.startswith("io.cloudbeaver.resources.drivers.base_"):
            cloudbeaverJarName = jar
            fz = zipfile.ZipFile("./plugins/" + jar, 'r')
            fz.extractall("./plugins/io.cloudbeaver.resources.drivers.base")
            os.remove("./plugins/" + cloudbeaverJarName)
        elif jar.startswith("org.jkiss.dbeaver.ext.generic_"):
            dbeaverJarName = jar
            fz = zipfile.ZipFile("./plugins/" + jar, 'r')
            fz.extractall("./plugins/org.jkiss.dbeaver.ext.generic")
            icons = os.listdir("./icons")
            for icon in icons:
                shutil.copy("./icons/" + icon, "./plugins/org.jkiss.dbeaver.ext.generic/icons")
            os.remove("./plugins/" + dbeaverJarName)
        else:
            shutil.rmtree("./plugins/" + jar)

    changePlugins("./plugins/org.jkiss.dbeaver.ext.generic/plugin.xml", "./plugins/io.cloudbeaver.resources.drivers.base/plugin.xml", "./drivers_plugins.csv")
    make_jar("./plugins/io.cloudbeaver.resources.drivers.base", "./plugins/" + cloudbeaverJarName)
    shutil.rmtree("./plugins/io.cloudbeaver.resources.drivers.base")
    make_jar("./plugins/org.jkiss.dbeaver.ext.generic", "./plugins/" + dbeaverJarName)
    shutil.rmtree("./plugins/org.jkiss.dbeaver.ext.generic")

    # 上传jar包
    make_targz('plugins.tar', "./plugins")
    shutil.rmtree("./plugins")
    jarFile = open('plugins.tar', 'rb')
    ok = container.put_archive(path='/opt/cloudbeaver/server/', data=jarFile)
    if not ok:
        raise Exception('上传jar包失败')
    jarFile.close()
    os.remove('plugins.tar')

    container.restart()  # 重启容器
    print("cloudbeaver服务已启动，访问端口：8978")
