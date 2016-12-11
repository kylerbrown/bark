from setuptools import setup, find_packages

setup(name='bark',
      version='0.1',
      description='tools for reading and writing BARK formatted data',
      url='http://github.com/kylerbrown/bark',
      author='Kyler Brown',
      author_email='kylerjbrown@gmail.com',
      license='GPL',
      #packages=find_packages('bark'),
      packages=['bark', 'bark.io'],
      zip_safe=False,
      entry_points = {
          'console_scripts' : [
              'bark-root=bark.barkutils:mk_root',
              'bark-entry=bark.barkutils:mk_entry',
              'bark-entry-from-prefix=bark.barkutils:entry_from_glob',
              'bark-clean-orphan-metas=bark.barkutils:clean_metafiles',
              'bark-scope=bark.barkscope:main',
              'csv-from-waveclus=bark.io.waveclus:_waveclus2csv',
              'csv-from-textgrid=bark.io.textgrid:textgrid2csv',
              'csv-from-lbl=bark.io.lbl:_lbl_csv',
              'bark-convert-rhd=bark.io.rhd.rhd2bark:bark_rhd_to_entry',
              'bark-convert-openephys=bark.io.openephys.kwik2dat:kwd_to_entry',
              ]
          }
      )
