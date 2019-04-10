import bark, pytest, numpy as np, os.path
from scipy.io import wavfile
from bark.io import datfromwav as dfw



'''Tests for testing successful: 
1. creation of wav files
2. creation of .dat and metadata file(.dat.metadata.yaml)
	
	Assuring:
1. sampling rates of wav and dat file are same
2. Data (numpy array) and dtype are same.
3. Attributes(if any) in .dat files are same as provided at creation of .dat file.'''

def test_dat_from_wav_int(tmpdir):
		
	# dtype: int array
	dir_path = tmpdir.strpath
	fname_wav = os.path.join(dir_path, 'test.wav')
	arr_int = np.random.randint(1000, size=(1,100))
	fname_dat = os.path.join(dir_path, 'test.dat')
	_helper_test(fname_wav, fname_dat, dir_path, arr_int)
	

def test_dat_from_wav_float(tmpdir):
	
	# dtype: float array
	dir_path = tmpdir.strpath
	fname_wav = os.path.join(dir_path, 'test.wav')
	arr_float = np.random.uniform(low=0.0, high=1000, size=(1,100))
	fname_dat = os.path.join(dir_path, 'test.dat')
	_helper_test(fname_wav, fname_dat, dir_path, arr_float)
	

def _helper_test(fname_wav, fname_dat, dir_path, data):
	rate = 48000
	#1.  Create wav file
	wavfile.write(fname_wav, rate, data)
	assert os.path.exists(fname_wav), 'File Not Found: test.wav'

	#2. Generate .dat and .dat.meta.yaml file
	attrs = {"name": "hello bark", "project": "bark"}
	dat_file = dfw.dat_from_wav(fname_wav, fname_dat, **attrs)
	assert os.path.exists(fname_dat), 'File Not Found: test.dat'
	assert os.path.exists(os.path.join(dir_path, 'test.dat.meta.yaml')), 'File Not Found: test.dat.meta.yaml'

	#3. Compare data, dtype, rate in .dat file
	assert np.array_equal(data, bark.read_sampled(fname_dat).data), 'Data in .wav and .dat files does not match' 
	assert data.dtype==bark.read_sampled(fname_dat).data.dtype, 'dtypes does not match'
	assert rate == bark.read_sampled(fname_dat).sampling_rate, 'Sampling rates does not match'
	assert 'hello bark' == bark.read_sampled(fname_dat).attrs['name'], 'name attribute does not match'
	assert 'bark' == bark.read_sampled(fname_dat).attrs['project'], 'project attribute does not match'
