# CloudbeaverTool
A Tool for Expanding Cloudbeaver Database Drivers

在AddNewDrivers文件夹下有几个文件，分别作用如下：
- drivers:存放驱动文件，每种数据库驱动放在对应id的文件夹下，注意id要保证唯一
- icons:存放数据库图标
- AddNewDrivers.py:扩展数据库脚本
- drivers_plugins.csv:数据库连接基本信息
  
  - id:数据库唯一id，与drivers下文件夹名称对应
  - label:数据库名称，在cloudbeaver添加数据库时显示
  - icon:数据库图标文件
  - class:数据库驱动类
  - sampleURL:数据库连接示例URL
  - defaultPort:默认端口号
  - description:数据库描述

## 如何扩展数据库？

**_请先安装Docker_**

1. 首先需要准备好要扩展的数据库驱动、图标文件并放到对应的文件夹中，并在drivers_plugins.csv中填写好信息
2. 进入AddNewDrivers目录

    ```shell
    python AddNewDrivers.py
    ```
    
    如果提示缺少docker包，请先安装docker包
    
    ```shell
    pip install docker
    ```
    
    如果提示未找到cloudbeaver镜像，可执行 `sudo docker pull dbeaver/cloudbeaver:latest` 手动拉取，也可执行以下命令让脚本拉取，此命令同样适用于更新镜像版本：
    
    ```shell
    python AddNewDrivers.py --pull true
    
    python AddNewDrivers.py -p t   # 简写形式
    ```
    
    脚本执行成功后会显示：
    
    ```shell
    成功扩展：达梦
    成功扩展：神舟通用
    cloudbeaver服务已启动，访问端口：8978
    ```
    
    访问 http://localhost:8978/#/admin/connections 进入管理界面
