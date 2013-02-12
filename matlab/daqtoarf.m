function [] = daqtoarf(exptcnf)
% DAQTOARF Convert daqfile data into ARF format
%
% DAQTOARF(exptcnf) imports the data using the metadata stored in
% exptcnf. The format of the file is a two-column, tab-delimited table
% with fields in the first column and values in the second.
% Required fields are prefix, date, slice, cell. Other important
% fields are bird, experimenter, area, and type.
%
% Copyright (C) 2011 Daniel Meliza <dmeliza@dylan.uchicago.edu>
% Created 2011-04-06

% parse metadata file
fid = fopen(exptcnf,'rt');
mdata = struct;
while ~feof(fid)
  s = fgetl(fid);
  [k,v] = strtok(s,char(9));
  if any(strcmp(k,{'slice','cell'}))
    mdata.(k) = str2num(v);
  else
    mdata.(k) = strtrim(v);
  end
end
fclose(fid);

warning('off','MATLAB:dispatcher:UnresolvedFunctionHandle');
warning('off','MATLAB:unknownElementsNowStruc');
warning('off','MATLAB:elementsNowStruc');
% create the arf file
arfname = sprintf('%s_%d_%d.arf',mdata.date,mdata.slice,mdata.cell);
fid = arfopenfile(arfname,'w');

[pn fn] = fileparts(exptcnf);
if isempty(pn), pn='.';, end

entry_num = 0;
sdirs = dir(fullfile(pn,[mdata.prefix '*']));
for i = 1:length(sdirs)
  fprintf(1,'%s -- ',sdirs(i).name);
  % in each directory a file named "%s-params.mat" will indicate
  % the name of the experiment
  mfile = dir(fullfile(pn,sdirs(i).name,'*-params.mat'));
  if isempty(mfile)
    fprintf(1,'no params.mat file\n');
    continue
  end
  entry_protocol = mfile(1).name(1:end-11);
  fprintf(1,entry_protocol)
  exptparams = load(fullfile(pn,sdirs(i).name,mfile(1).name));
  dfiles = getsortedfiles(fullfile(pn,sdirs(i).name));
  for j = 1:length(dfiles)
    entry_name = sprintf('e%s_%d_%d_%d',mdata.date,mdata.slice,mdata.cell,entry_num);
    fprintf(1,'\n* %s -> %s', dfiles(j).name, entry_name);
    dfile = fullfile(pn,sdirs(i).name,dfiles(j).name);
    ifo = daqread(dfile,'info');
    % update some attributes if this is the first daqfile loaded
    if i==1 && j==1
      file_mdata = mdata;
      file_mdata.skew = ifo.ObjInfo.ChannelSkew;
      file_mdata.daq = ifo.HwInfo.DeviceName;
      file_mdata.daq_bits = ifo.HwInfo.Bits;
      gid = H5G.open(fid,'/');
      make_attrs(gid,file_mdata)
      H5G.close(gid)
    end

    entry_secs = 86400*(datenum(ifo.ObjInfo.InitialTriggerTime) - datenum(1970,1,1));
    entry_timestamp = [fix(entry_secs) rem(entry_secs,1)*1e6];
    entry_mdata = struct('sourcefile',dfile,'protocol',entry_protocol);
    for k = {'stimulus','ep_interval','max_pos_cur','max_neg_cur'}
      if isfield(exptparams,k{1})
        entry_mdata.(k{1}) = exptparams.(k{1}).value;
      end
    end
    % set comment parameter to current stimulus
    if isfield(exptparams,'stim_list')
      entry_stim = exptparams.stim_list.value{1}{mod(j-1,length(exptparams.stim_list.value{1}))+1};
      entry_mdata.protocol = [entry_mdata.protocol ': ' entry_stim];
    elseif isfield(exptparams,'stimulus')
      entry_mdata.protocol = [entry_mdata.protocol ': ' exptparams.stimulus.value];
    end
    eid = arfopenentry(fid, entry_name, entry_timestamp, entry_mdata);
    d = daqread(dfile);
    [nchan ncol] = size(d);
    for k = 1:ncol
      data_name = ifo.ObjInfo.Channel(k).ChannelName;
      data_units = ifo.ObjInfo.Channel(k).Units;
      data_srate = ifo.ObjInfo.SampleRate;
      data_types = 5;
      data_mdata = struct('input_range', ...
                          [ifo.ObjInfo.Channel(k).InputRange],...
                          'scaling', ...
                          [ifo.ObjInfo.Channel(k).NativeScaling]);
      arfwriteentry(eid,data_name,d(:,k),data_units,data_types, ...
                    data_srate,'H5T_NATIVE_DOUBLE',data_mdata);
    end
    arfcloseentry(eid);
    entry_num = entry_num + 1;
  end
  fprintf(1,'\n');
end

arfclosefile(fid);
warning('on','MATLAB:dispatcher:UnresolvedFunctionHandle');
warning('on','MATLAB:unknownElementsNowStruc');
warning('on','MATLAB:elementsNowStruc');

function [dfiles] = getsortedfiles(sdir)
% load each of the daq files in turn and sort them by trigger time
dfiles = dir(fullfile(sdir,'*.daq'));
ttimes = [];
for i = 1:length(dfiles)
    ifo = daqread(fullfile(sdir,dfiles(i).name),'info');
    ttimes(i) = datenum(ifo.ObjInfo.InitialTriggerTime);
end
[~, ind] = sort(ttimes);
dfiles = dfiles(ind);
