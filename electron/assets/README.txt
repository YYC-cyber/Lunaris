Lunaris 桌面端图标资源（已由根目录 icon.jpg 生成）

- icon.png   512×512  系统托盘图标（运行时用）
- icon.icns  macOS 应用图标（electron-builder 打包 dmg 用）
- icon.ico   256×256  Windows 应用图标（打包 exe 用，PNG 压缩）

重新生成（macOS）：
  sips -s format png -z 512 512 ../../icon.jpg --out icon.png
  # icns：见 scripts 或手动 iconutil；ico：用 Python 打包 PNG 进 ICO 容器

生产构建后端地址：
  打包前需指定后端地址，否则 file:// 下前端无法连后端：
  在 frontend/ 目录执行：VITE_API_BASE=https://你的后端域名 npm run build
