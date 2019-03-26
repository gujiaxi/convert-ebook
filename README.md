# Convert-ebook 

使用Python3编写的电子书格式转换工具，将未加密的AZW3格式无损转换为EPUB及MOBI。

## 用法
  
  ```shell
  ./convert-ebook.py foo.azw3
  ```
## MOBI格式

转换得到的MOBI文件实际上是包含KF7和KF8两种标准的混合格式（对应calibre下将输出格式设置为both的情况下转换得到的MOBI文件），采用混合格式的原因在于通过邮件发送电子书到Kindle时Amazon会拒绝接收纯的KF8格式，但是对于这种混合格式它却会自动提取出其中的KF8部分，唯一的缺点是在Kindle上不会显示封面（文件格式中确实包含书籍封面只是没有被解析）。

## 注意

- 该项目使用python3编写，未对python2进行兼容。
- 执行脚本后，会扫描该文件或该目录下所有的azw3文件（包括子目录），并执行转换。转换后的文件会写入到azw3所在的目录。如果写入时已经存在同名文件，旧文件会被覆盖掉。
- 默认同时处理 **CPU核心数*2** 个转换任务。
- 该项目主要由下列两个核心组建驱动：
  - [kindleunpack](https://github.com/kevinhendricks/KindleUnpack)用于转换AZW3为EPUB。
  - [kindlegen](http://www.amazon.com/gp/feature.html?docId=1000765211)用于转换EPUB为MOBI。
