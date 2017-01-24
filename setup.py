from setuptools import setup, find_packages

setup(name='bark',
      version='0.1',
      description='tools for reading and writing BARK formatted data',
      url='http://github.com/kylerbrown/bark',
      author='Kyler Brown',
      author_email='kylerjbrown@gmail.com',
      license='GPL',
      #packages=find_packages('bark', 'bark.io'),
      packages=['bark',
          'bark.tools',
          'bark.io',
          'bark.io.rhd',
          'bark.io.openephys',
          ],
      zip_safe=False,
      entry_points = {
          'console_scripts' : [
              'bark-root=bark.tools.barkutils:mk_root',
              'bark-entry=bark.tools.barkutils:mk_entry',
              'bark-entry-from-prefix=bark.tools.barkutils:entry_from_glob',
              'bark-clean-orphan-metas=bark.tools.barkutils:clean_metafiles',
              'bark-scope=bark.tools.barkscope:main',
              'csv-from-waveclus=bark.io.waveclus:_waveclus2csv',
              'csv-from-textgrid=bark.io.textgrid:textgrid2csv',
              'csv-from-lbl=bark.io.lbl:_lbl_csv',
              'csv-from-plexon-csv=bark.io.plexon:_plexon_csv_to_bark_csv',
              'bark-convert-rhd=bark.io.rhd.rhd2bark:bark_rhd_to_entry',
              'bark-convert-openephys=bark.io.openephys.kwik2dat:kwd_to_entry',
              'bark-split=bark.tools.barksplit:_main',
              'dat-decimate=bark.tools.barkutils:rb_decimate',
              ]
          }
      )
