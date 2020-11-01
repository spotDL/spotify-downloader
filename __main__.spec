# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


a = Analysis(['spotdl\\__main__.py'],
             pathex=['D:\\Projects\\GitHub\\spotify-downloader'],
             binaries=[],
             datas=[(r'D:\Software\ffmpeg-4.3.1-win64-static\ffmpeg-4.3.1-win64-static\bin\*', '.\\')],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='spotdl',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=True )