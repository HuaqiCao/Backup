% extracts signal and baseline data from a CSV file based on a threshold.   
% saves the results in a new directory named 'highpass'（code location）.

% Select a CSV file
[filename, path] = uigetfile('*.csv', 'Select CSV file');
if isequal(filename, 0)
    return;
end

% Read the CSV file
data = readmatrix(fullfile(path, filename));

% Extract data from row 5 onward
time = data(5:end, 1);
volt = data(5:end, 2);

% Design high-pass Butterworth filter
fs = 1 / (time(21) - time(20)); % Sampling frequency
fc = 0.1;                        % Cutoff frequency (Hz)
[b, a] = butter(2, fc / (fs / 2), 'high');

% Apply the filter
filtered_volt = filtfilt(b, a, volt);

% Create output directory if not exist
if ~exist('highpass', 'dir')
    mkdir('highpass');
end

% Prepare output filename
new_filename = fullfile('highpass', ['highpass_' filename]);

% Write 4 blank header lines and then the filtered data
fid = fopen(new_filename, 'w');
fprintf(fid, '\n\n\n\n'); % Write 4 blank lines
fclose(fid);
writematrix([time, filtered_volt], new_filename, 'WriteMode', 'append');
