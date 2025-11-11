% Get the filenames and path of the selected CSV files
[filenames, path] = uigetfile('*.csv', 'Select CSV files', 'MultiSelect', 'on');

% If the user clicked cancel, return
if isequal(filenames,0)
   return;
end

% If only one file was selected, convert it to a cell array
if ~iscell(filenames)
    filenames = {filenames};
end

% Initialize cell array for legends
legends = cell(1,length(filenames)); 

% Loop over selected files
for i = 1:length(filenames)
    % Get the current filename and read in the data
    filename = filenames{i};
    data = readmatrix(fullfile(path, filename));

    % Remove the first 4 rows of data and reshape into a vector
    data = data(5:end, :); 
    data = data(:,2);

    % Set parameters for the PSD calculation
    sen = 1.000;    % Sensitivity in V/g
    g = 9.81;       % m/s2
    wint = 5;       % Window time in s
    gain = 100.003;       % Default gain
    fs = 10000;     % Sampling frequency
    % Set the gain based on the filename
    if contains(filename,"1gain")
        gain = 1;
    elseif contains(filename,"10gain")
        gain = 10.003;
    elseif contains(filename,"100gain")
        gain = 100.122;
    end
    % Set the fs based on the filename
% Search for the pattern "(\d+)fs" in the filename
match = regexp(filename, '(\d+)fs', 'match');
% If a match is found, extract the digits and convert to a double
if ~isempty(match)
    fs_str = match{1}(1:end-2); % Remove the "fs" suffix
    fs = str2double(fs_str);
end
    window_size = wint*fs; % Window size in samples
%     nfft = window_size; % Number of FFT points
    nfft = 2^nextpow2(window_size); % Number of FFT points
    overlap = nfft/2; % Overlap
    f = (0:nfft/2-1)*fs/nfft; % Frequency vector
    data = data / (gain * sen);%transfer data from V to g

    % Apply Hanning window to data
    window = hann(window_size);
    window = window./sqrt(mean(window.^2)); % normalize Hanning window
    data_windowed = buffer(data, window_size, overlap, 'nodelay');
    data_windowed = data_windowed .* window;

    % Compute power spectrum density
    psd = zeros(nfft/2, size(data_windowed, 2));
    for j = 1:size(data_windowed, 2)
        fft_data = fft(data_windowed(:,j), nfft);
%         psd(:,j) = abs(fft_data(1:nfft/2)).^2 / (fs*nfft*norm(window)^2);
        psd(:,j) = abs(fft_data(1:nfft/2)).^2 / (fs*nfft);
        psd(2:end-1,j) = 2*psd(2:end-1,j);

    end
%     psd(2:end-1) = 2*psd(2:end-1);
    psd = mean(psd, 2);

    % Plot PSD
    loglog(f, sqrt(psd)); % Plot the power spectrum density
    % Set legend for current file
    [~, name, ~] = fileparts(filename);
    legends{i} = name;

    hold on;
end

% Plot legend with all file names
legend(legends,'FontSize',18,'Location','northeast','Interpreter','none'); % Plot the legend with all file names

xlabel("$Frequency (Hz)$","Interpreter","latex"); % x-axis label
ylabel("$PSD\left[g/\sqrt{Hz}\right]$","Interpreter","latex"); % y-axis label
grid on; % show grid
title("Power Spectrum Density"); % plot title

hold off;
