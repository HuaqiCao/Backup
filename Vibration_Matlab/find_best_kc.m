% Vertical vibration isolation design with fatigue limit and damping optimization
% Computes spring parameters, damping coefficient, and isolation performance

% === BASE PARAMETERS ===
M = 12.6;                % Load mass (kg)
g = 9.81;                % Gravitational acceleration (m/s^2)

% Material Properties (304)
G = 77.5e9;              % Shear modulus (Pa)
rho = 7955;              % Density (kg/m^3)
sigma_b = 630e6;         % Tensile yield strength (Pa)

% Target Natural Frequency
f0_vertical = 1.1;                  
k_target = M * (2 * pi * f0_vertical)^2;
L_Tower = 0.46;          % Tower height (m)

% Search Ranges
d_wire_range = 1e-3:1e-3:5e-3;      % Wire diameter (1-5mm)
d_in_range = 5e-3:1e-3:9.5e-2;      % Inner diameter (5-95mm)
d_hook_range = 1e-3:1e-3:5e-3;      % Hook diameter (1-5mm)
r_hook_range = 3e-3:1e-3:10e-3;     % Hook radius (3-10mm)

results = [];
best_freq = Inf;         
best_params = [];
best_L0 = NaN;                       % Save best spring free length (m)
material_name = 'Stainless Steel';   % Material name (304 stainless steel)

% Spring design optimization loop
for i = 1:length(d_wire_range)
    for j = 1:length(d_in_range)
        for m = 1:length(d_hook_range)
            for n = 1:length(r_hook_range)
                d_wire = d_wire_range(i);
                d_in   = d_in_range(j);
                d_hook = d_hook_range(m);
                r_hook = r_hook_range(n);

                d_out = d_in + 2 * d_wire;
                D = (d_in + d_out) / 2;
                c_index = D / d_wire;

                if d_out > 0.1
                    continue;
                end

                n_calc = (G * d_wire^4) / (8 * D^3 * k_target);
                n_eff_options = unique(round([n_calc+1.5, ceil(n_calc), ceil(n_calc)+1]));

                for k = 1:length(n_eff_options)
                    n_eff = n_eff_options(k);
                    n_total = n_eff + 2;

                    k_actual = (G * d_wire^4) / (8 * D^3 * n_eff);

                    A_coil = pi * (d_wire^2 / 4);         
                    L_wire = n_eff * pi * D;              
                    m_s = rho * A_coil * L_wire;          
                    m_eq = M + (1/3) * m_s;               

                    delta_static = m_eq * g / k_actual;
                    L_eq = n_total * d_wire + delta_static + 2 * d_hook + 2 * r_hook;

                    if L_eq > 0.35
                        continue;
                    end
                    L0 = n_total * d_wire + 2 * d_hook + 2 * r_hook;
                    L = L_eq + L_Tower * 2 / 5;  
                    pitch = (L0 - 2 * d_hook - 2 * r_hook) / n_eff;

                    f0_radial = sqrt(g / L) / (2 * pi);

                    F_max = m_eq * g;
                    Kw = (4*c_index - 1)/(4*c_index -4) + 0.615/c_index;
                    tau_e = Kw * (8 * F_max * D) / (pi * d_wire^3);

                    if tau_e > 0.45 * sigma_b 
                        continue;
                    end

                    kappa_3 = (4 * c_index^2 - c_index - 1) / (4 * c_index * (c_index - 1));
                    kappa_3_prime = kappa_3 + 1 / (4 * c_index);
                    sigma_max = kappa_3_prime * (16 * D * F_max) / (pi * d_wire^3);

                    if sigma_max >= 0.7 * sigma_b
                        continue;
                    end

                    actual_freq = sqrt(k_actual/m_eq)/(2*pi);

                    results = [results;
                      d_wire*1000, d_in*1000, d_out*1000, D*1000, ...
                      c_index, n_total, n_eff, pitch*1000, ...
                      L0*1000, L_eq*1000, A_coil*1e6, ...
                      m_s, m_eq, k_actual, ...
                      actual_freq, ...
                      tau_e/1e6, f0_radial, sigma_max/1e6];

                    if actual_freq < f0_vertical && actual_freq < best_freq
                            best_freq = actual_freq;
                            best_params = [d_wire, D, n_total, n_eff, m_s, m_eq, k_actual, ...
                                actual_freq, f0_radial, sigma_max, L]; 
                            best_L0 = L0;
                    end
                end
            end
        end
    end
end

if ~isempty(results)
    % ===== DISPLAY RESULTS =====
    header = {'Wire_d_mm', 'Inner_d_mm', 'Outer_d_mm', 'Mean_D_mm', 'Index_c', ...
        'Total_turns', 'Eff_turns', 'Pitch_mm', 'Free_len_L0_mm', ...
        'Assembly_len_Leq_mm', 'Area_mm2', 'Spring_mass_kg', ...
        'Eff_mass_kg', 'Stiffness_N_m', 'Freq_Hz', ...
        'Tau_max_MPa', 'Radial_freq_Hz', 'Sigma_max_MPa'};
    
    fprintf('\n%-10s %-10s %-10s %-10s %-10s %-10s %-10s %-10s %-10s %-10s %-10s %-12s %-12s %-10s %-10s %-12s %-10s %-10s\n', header{:});
    
    for i = 1:size(results,1)
        fprintf('%-10.2f %-10.2f %-10.2f %-10.2f %-10.2f %-10d %-10d %-10.2f %-10.2f %-10.2f %-10.2f %-12.4f %-12.4f %-10.1f %-10.2f %-12.2f %-10.2f %-10.2f\n', results(i,:));
    end

    if ~isempty(best_params)
        fprintf('\n=== Optimal Spring Design ===\n', best_freq);
        fprintf('Wire Diameter: %.1f mm\n', best_params(1)*1000);
        fprintf('Mean Diameter: %.1f mm\n', best_params(2)*1000);
        fprintf('Total Turns: %d (Effective Turns: %d)\n', best_params(3), best_params(4));
        fprintf('Spring Mass: %.4f kg\n', best_params(5));
        fprintf('Effective Mass: %.4f kg\n', best_params(6));
        fprintf('Stiffness: %.2f N/m\n', best_params(7));
        fprintf('Axial Natural Freq: %.4f Hz\n', best_params(8));
        fprintf('Radial Natural Freq: %.2f Hz\n', best_params(9));
        fprintf('Spring Length L = %.4f m\n', best_params(11));
        fprintf('Max Tensile Stress: %.2f MPa (Limit: %.2f MPa)\n', best_params(10)/1e6, 0.7*sigma_b/1e6);
    end
else
    disp('No design found meeting all constraints.');
end

% ====== DAMPING OPTIMIZATION ======
k_actual = best_params(7);   
m_eq = best_params(6);       
fn = best_params(8);         
wn = 2*pi*fn;                

c_range = linspace(0.1, 1000, 10000);  
f_range = 0:0.1:1000;         
omega_range = 2*pi*f_range;

best_c = 0;
min_T_energy = Inf;          
best_T = [];

T_energy_values = zeros(size(c_range));
zeta_values = zeros(size(c_range));

C_constant = 2*sqrt(k_actual*m_eq);

for idx = 1:length(c_range)
    c = c_range(idx);
    zeta = c / C_constant;
    zeta_values(idx) = zeta;

    T = zeros(size(omega_range));
    for j = 1:length(omega_range)
        omega = omega_range(j);
        r = omega/wn;

        numerator = sqrt(1 + (2*zeta*r)^2);
        denominator = sqrt((1 - r^2)^2 + (2*zeta*r)^2);
        T(j) = numerator / denominator;
    end

    T_energy = trapz(f_range, T.^2);
    T_energy_values(idx) = T_energy;

    if T_energy < min_T_energy
        min_T_energy = T_energy;
        min_peak_T = max(T);
        min_avg_T = mean(T);
        best_c = c;
        best_T = T;
        best_zeta = zeta;
    end
end

% ===== DISPLAY OPTIMAL DAMPING =====
fprintf('\n=== Optimal Damping Parameters ===\n');
fprintf('Best Damping Coefficient c = %.2f N·s/m\n', best_c);
fprintf('Corresponding Damping Ratio ζ = %.4f\n', best_zeta);
fprintf('Minimum Peak Transmission Ratio = %.4f\n', min_peak_T);
fprintf('Minimum Avg Transmission Ratio = %.4f\n', min_avg_T);
fprintf('Minimum Energy (0–100 Hz) = %.4f\n', min_T_energy);

% === SAVE BEST SPRING PARAMS TO EXCEL ===
% Use the chosen CSV's file name as prefix; save in the same folder
if exist('filePath','var') ~= 1
    filePath = pwd; name = datestr(now,'yyyymmdd_HHMMSS'); % Fallback if CSV not selected before
end

springHeader = {'Material','Wire Diameter (mm)','Mean Diameter (mm)', ...
                'Effective Turns','Original Length (m)', ...
                'Stiffness (N/m)','Damping Coefficient (N·s/m)'};
springRow = { ...
    material_name, ...
    round(best_params(1)*1000,2), ...   % Wire dia (mm)
    round(best_params(2)*1000,2), ...   % Mean dia (mm)
    best_params(4), ...                 % Effective turns
    round(best_L0,4), ...               % Free length (m)
    round(best_params(7),2), ...        % k (two decimals)
    round(best_c,2) };                  % c (two decimals)

% — Path and file-name clean up (trim spaces and illegal chars) —
if exist('filePath','var') ~= 1 || isempty(filePath)
    filePath = pwd; 
end
if exist('name','var') ~= 1 || isempty(name)
    name = datestr(now,'yyyymmdd_HHMMSS'); 
end
filePath = strtrim(char(filePath));              % Trim spaces
name     = strtrim(char(name));
name     = regexprep(name,'[^\w\-.]','_');       % Non [A-Za-z0-9_.-] -> underscore

springXlsx = fullfile(filePath, sprintf('%s_best_spring.xlsx', name));
try
    writecell([springHeader; springRow], springXlsx);
catch ME
    warning('写入失败：%s\n-> %s\n改为写到当前目录。', springXlsx, ME.message);
    springXlsx = fullfile(pwd, sprintf('%s_best_spring.xlsx', name));
    writecell([springHeader; springRow], springXlsx);
end
fprintf('Best spring parameters saved: %s\n', springXlsx);

% === GLOBAL PLOT SETTINGS ===
fontEN = 'Arial';
set(0,'defaultAxesFontName',fontEN);
set(0,'defaultTextFontName',fontEN);
set(0,'defaultLegendFontName',fontEN);
set(0,'defaultUIControlFontName',fontEN);
set(0,'defaultAxesFontSize',12);
set(0,'defaultTextInterpreter','none');     
set(0,'defaultLegendInterpreter','none');   

figSize = [1, 1, 10, 5];  % in inches

% === Figure 1: Frequency Response Curve ===
figure('Name', 'Transmission Ratio Curve', 'Units', 'inches', 'Position', figSize);

r_range = omega_range / wn;

plot(r_range, best_T, 'b-', 'LineWidth', 2, 'DisplayName', 'Transmission Ratio');
hold on;
plot([1, 1], [0, max(best_T)], 'r--', 'LineWidth', 1.5, 'DisplayName', 'Natural Frequency');
r_sqrt2 = sqrt(2);
plot([r_sqrt2, r_sqrt2], [0, max(best_T)], 'g--', 'LineWidth', 1.5, 'DisplayName', '√2×Natural Frequency');

xlabel('Frequency Ratio (r = ω/ω_n)');
ylabel('Transmission Ratio T');
title('Frequency Response Curve', 'FontSize', 24);
text(0.6, 0.6, '$T = \frac{\sqrt{1 + (2\zeta r)^2}}{\sqrt{(1 - r^2)^2 + (2\zeta r)^2}}$', ...
    'Interpreter', 'latex', 'FontSize', 20, 'Units', 'normalized');
legend('show', 'Location', 'best', 'FontSize', 16);
grid on;
xlim([0, 5]);
ylim([0, max(best_T) * 1.1]);

% === Figure 2: Transmission Energy vs Damping Coefficient ===
figure('Name', 'Energy vs Damping Coefficient', 'Units', 'inches', 'Position', figSize);
semilogx(c_range, T_energy_values, 'b-', 'LineWidth', 2);
hold on;
plot([best_c, best_c], [min(T_energy_values), max(T_energy_values)], 'r--', 'LineWidth', 1.5);
xlabel('Damping Coefficient c (N·s/m)');
ylabel('Transmission Energy E (0–1000 Hz)');
title('Energy vs. Damping Coefficient (Vertical)', 'FontSize', 24);
text(0.05, 0.75, '$E = \int_{0}^{1000} T^2(f) df$', ...
    'Interpreter', 'latex', 'FontSize', 18, 'Units', 'normalized');
text(0.05, 0.65, sprintf('$c_{best} = %.2f$ N$\\cdot$s/m', best_c), ...
    'Interpreter', 'latex', 'FontSize', 18, 'Units', 'normalized');
text(0.05, 0.55, sprintf('$\\zeta_{best} = %.4f$', best_zeta), ...
    'Interpreter', 'latex', 'FontSize', 18, 'Units', 'normalized');
legend('Transmission Energy', 'Optimal Damping Coefficient', 'Location', 'best', 'FontSize', 16);
xlim([0, 1000]);
grid on;

% === Figure 3: Transmission Energy vs Damping Ratio ===
figure('Name', 'Energy vs Damping Ratio', 'Units', 'inches', 'Position', figSize);
plot(zeta_values, T_energy_values, 'b-', 'LineWidth', 2);
hold on;
plot([best_zeta, best_zeta], [min(T_energy_values), max(T_energy_values)], 'r--', 'LineWidth', 1.5);
xlabel('Damping Ratio $\zeta$', 'Interpreter', 'latex');
ylabel('Transmission Energy E (0–1000 Hz)');
title('Energy vs. Damping Ratio (Vertical)', 'FontSize', 24);
text(0.2, 0.85, '$E = \int_{0}^{1000} T^2(f) df$', ...
    'Interpreter', 'latex', 'FontSize', 18, 'Units', 'normalized');
text(0.2, 0.75, sprintf('$\\zeta_{best} = %.4f$', best_zeta), ...
    'Interpreter', 'latex', 'FontSize', 18, 'Units', 'normalized');
legend('Transmission Energy', 'Optimal Damping Ratio', 'Location', 'best', 'FontSize', 16);
grid on;
xlim([0, 5]);
set(gca, 'FontName', 'Arial', 'FontSize', 12);

% ============== VIBRATION ISOLATION ANALYSIS ==============
% Select CSV file with acceleration data
[fileName, filePath] = uigetfile('*.csv', 'Select Source Acceleration CSV File');
if isequal(fileName, 0)
    error('User canceled file selection.');
end
fullFileName = fullfile(filePath, fileName);

% Read CSV file (keep first 4 header lines)
fid = fopen(fullFileName, 'r');
headerLines = cell(4,1);
for i = 1:4
    headerLines{i} = fgetl(fid);
end
fclose(fid);

% Read data
opts = detectImportOptions(fullFileName, 'NumHeaderLines', 4);
data = readmatrix(fullFileName, opts);
time = data(:, 1);
voltage = data(:, 2);  % Voltage signal

% Sensor parameters
gain = 100;         % Gain
sensitivity = 1.026; % Sensitivity (g/V)

% Convert to acceleration (g) - raw data before isolation
acc_base_g = voltage / ( gain * sensitivity );

% Convert to SI units and remove DC component
acc_base = acc_base_g * g;               % Convert to m/s^2
acc_base = acc_base - mean(acc_base);    % Remove DC offset

% Sampling parameters
dt = mean(diff(time));
fs = 1 / dt;
N = length(time);

% Vectorized full-spectrum FRF aligned with FFT bins (0..N-1)
k = (0:(N-1)).';                         % Column vector: N×1
omega_full = 2*pi*fs * (k / N);          % rad/s, N×1
s = 1i * omega_full;                     % N×1
H_full = (best_c .* s + k_actual) ./ (m_eq .* (s.^2) + best_c .* s + k_actual);  % N×1

% Frequency-domain filtering for isolated acceleration
fft_base = fft(acc_base(:));             % Ensure column vector N×1
fft_isolated = fft_base .* H_full;       % Elementwise multiply, sizes match N×1
acc_isolated = real(ifft(fft_isolated, 'symmetric'));  % Stable numeric; real result

% Remove DC component
acc_isolated = acc_isolated - mean(acc_isolated);

% ============== PLOT COMPARISON ==============
% Time-Domain Comparison
fig_time = figure('Name', 'Time-Domain Comparison of Acceleration', 'Units', 'inches', 'Position', figSize);
acc_base_g_detrend = acc_base / g;
plot(time, acc_base_g_detrend, 'b-', 'LineWidth', 1.5, 'DisplayName', 'Before Isolation on MXC_vertical @RT'); 
hold on;
plot(time, acc_isolated / g, 'r-', 'LineWidth', 1.5, 'DisplayName', 'After Isolation on MXC simulation_vertical @RT'); 
xlabel('Time (s)');
ylabel('Acceleration (g)');
title('Time-Domain Acceleration Comparison (Vertical)', 'FontSize', 24);
legend('show', 'Location', 'best', 'FontSize', 12);
grid on;
xlim([0 , 1]);

% ============== OUTPUT ISOLATED CSV FILE ==============
% Convert isolated acceleration to voltage signal
acc_isolated_g = acc_isolated / g; % Convert to g units
voltage_isolated = acc_isolated_g * sensitivity * gain;

% Create output filename
[~, name, ext] = fileparts(fileName);
outputFileName = fullfile(filePath, [name '_isolated' ext]);

% Write CSV file (with original headers)
fid = fopen(outputFileName, 'w');
for i = 1:4
    fprintf(fid, '%s\n', headerLines{i});
end
for i = 1:length(time)
    fprintf(fid, '%.6f,%.6f\n', time(i), voltage_isolated(i));
end
fclose(fid);

fprintf('Isolated acceleration data saved as: %s\n', outputFileName);

% ============== PSD AND LPSD ANALYSIS ==============
% Segment parameters
seglen = min(round(fs*10), N); 
window = hamming(seglen);
overlap = round(seglen / 2);
nfft = seglen; 

% --- Welch number of segments N ---
L     = seglen;           % window length
nover = overlap;
N_sig = numel(acc_base);
N_win = floor((N_sig - nover) / (L - nover));
fprintf('Welch averaging windows N = %d\n', N_win);

% PSD calculation
[pxx_base, f] = pwelch(acc_base, window, overlap, nfft, fs);
[pxx_isolated, ~] = pwelch(acc_isolated, window, overlap, nfft, fs);

% ===== Parseval checks (base & isolated) =====
var_time_base     = var(acc_base);
var_freq_base     = trapz(f, pxx_base);
var_time_isolated = var(acc_isolated);
var_freq_isolated = trapz(f, pxx_isolated);

fprintf('Base   Parseval: var_time=%.6g, var_freq=%.6g, ratio=%.3f\n', ...
        var_time_base, var_freq_base, var_time_base/var_freq_base);
fprintf('Iso    Parseval: var_time=%.6g, var_freq=%.6g, ratio=%.3f\n', ...
        var_time_isolated, var_freq_isolated, var_time_isolated/var_freq_isolated);

% LPSD calculation (normalized units)
lpsd_base = sqrt(pxx_base) / g;
lpsd_isolated = sqrt(pxx_isolated) / g;
lpsd_base_disp = g ./ ((2*pi*f).^2) .* lpsd_base;
lpsd_isolated_disp = g ./ ((2*pi*f).^2) .* lpsd_isolated;
lpsd_base_disp(f==0) = 0;
lpsd_isolated_disp(f==0) = 0;

% Auto-set xlim range
fmax_plot = max(f(f < fs/2));

% Plot PSD comparison
fig_psd = figure('Name', 'PSD Comparison', 'Units', 'inches', 'Position', figSize);
loglog(f, pxx_base / g^2, '-', 'Color', [0.1,0.2,0.8], 'LineWidth', 1.5, 'DisplayName', 'Before Isolation on MXC_vertical @RT');
hold on;
loglog(f, pxx_isolated / g^2, '--', 'Color', [0.8,0.2,0.2], 'LineWidth', 1.5, 'DisplayName', 'After Isolation on MXC simulation_vertical @RT');
legend('show'); grid on; xlabel('Frequency (Hz)'); ylabel('PSD [g^2/Hz]');
title('Power Spectral Density  (Vertical ，PT_on )','FontSize', 24); xlim([0.1, fmax_plot]);

% Plot acceleration LPSD
fig_acc_lpsd = figure('Name', 'LPSD of Acceleration', 'Units', 'inches', 'Position', figSize);
loglog(f, lpsd_base, '-', 'Color', [0.1,0.2,0.8], 'LineWidth', 1.5, 'DisplayName', 'Before Isolation on MXC_vertical @RT');
hold on;
loglog(f, lpsd_isolated, '--', 'Color', [0.8,0.2,0.2], 'LineWidth', 1.5, 'DisplayName', 'After Isolation on MXC simulation_vertical @RT');
legend('show'); grid on; xlabel('Frequency (Hz)'); ylabel('LPSD [g/√Hz]');
title('Acceleration LPSD  (Vertical , PT_on)','FontSize', 24); xlim([0.1, fmax_plot]);

% Plot displacement LPSD
fig_disp_lpsd = figure('Name', 'LPSD of Displacement', 'Units', 'inches', 'Position', figSize);
loglog(f, lpsd_base_disp * 1e9, '-', 'Color', [0.1,0.2,0.8], 'LineWidth', 1.5, 'DisplayName', 'Before Isolation on MXC_vertical @RT');
hold on;
loglog(f, lpsd_isolated_disp * 1e9, '--', 'Color', [0.8,0.2,0.2], 'LineWidth', 1.5, 'DisplayName', 'After Isolation on MXC simulation_vertical @RT');
legend('show'); grid on; xlabel('Frequency (Hz)'); ylabel('LPSD [nm/√Hz]');
title('Displacement LPSD  (Vertical , PT_on)','FontSize', 24); xlim([0.1, fmax_plot]);

% ===== RMS frequency band analysis  (use PSD directly) =====
band_edges = [1, 40; 40, 1000; 1, 1000];
band_names = {'[1–40] Hz','[40–1k] Hz','[1–1k] Hz'};
nBands = size(band_edges, 1);

% Prepare displacement PSD from acceleration PSD (avoid f=0)
pxx_base_disp     = pxx_base     ./ (2*pi*f).^4;   % (m^2/Hz)
pxx_isolated_disp = pxx_isolated ./ (2*pi*f).^4;   % (m^2/Hz)
pxx_base_disp( f==0 )     = 0;
pxx_isolated_disp( f==0 ) = 0;

% Initialize arrays
RMS_base_acc      = zeros(1, nBands);
RMS_isolated_acc  = zeros(1, nBands);
RMS_base_disp     = zeros(1, nBands);
RMS_isolated_disp = zeros(1, nBands);

for iBand = 1:nBands
    lo = band_edges(iBand,1);
    hi = band_edges(iBand,2);
    hi = min(hi, max(f));

    % Band edge rules: band1=[1,40); band2=(40,1000]; full=[1,1000]
    if iBand == 1
        idx = (f >= lo) & (f <  hi);      % [1,40)
    elseif iBand == nBands
        idx = (f >= lo) & (f <= hi);      % [1,1000]
    else
        idx = (f >  lo) & (f <= hi);      % (40,1000]
    end

    % --- Integrate PSD directly (equivalent to integrating LPSD^2) ---
    % Acceleration: convert PSD to g-based, then RMS -> µg
    RMS_base_acc(iBand)     = sqrt(trapz(f(idx), pxx_base(idx))     / g^2) * 1e6;
    RMS_isolated_acc(iBand) = sqrt(trapz(f(idx), pxx_isolated(idx)) / g^2) * 1e6;

    % Displacement: use displacement PSD (m^2/Hz), RMS -> nm
    RMS_base_disp(iBand)     = sqrt(trapz(f(idx), pxx_base_disp(idx)))     * 1e9;
    RMS_isolated_disp(iBand) = sqrt(trapz(f(idx), pxx_isolated_disp(idx))) * 1e9;
end

% Print RMS results
fprintf('\n=== RMS Comparison Summary (PT_on) ===\n');
fprintf('%-16s %-12s %-12s %-10s | %-12s %-12s %-10s\n', ...
    'Frequency Band','Before Acc (\xB5g)','After Acc (\xB5g)','Reduction (%)', ...
    'Before Disp (nm)','After Disp (nm)','Reduction (%)');

for iBand = 1:nBands
    red_acc  = (RMS_base_acc(iBand)  - RMS_isolated_acc(iBand))  ./ max(RMS_base_acc(iBand),  eps) * 100;
    red_disp = (RMS_base_disp(iBand) - RMS_isolated_disp(iBand)) ./ max(RMS_base_disp(iBand), eps) * 100;
    fprintf('%-16s %-12.2f %-12.2f %-10.2f | %-12.2f %-12.2f %-10.2f\n', ...
        band_names{iBand}, RMS_base_acc(iBand), RMS_isolated_acc(iBand), red_acc, ...
        RMS_base_disp(iBand), RMS_isolated_disp(iBand), red_disp);
end

% === SAVE RMS SUMMARY TO EXCEL ===
red_acc  = (RMS_base_acc  - RMS_isolated_acc ) ./ max(RMS_base_acc,  eps) * 100;
red_disp = (RMS_base_disp - RMS_isolated_disp) ./ max(RMS_base_disp, eps) * 100;

rmsHeader = {'Frequency Band','Before Acc (µg)','After Acc (µg)','Reduction (%)', ...
             'Before Disp (nm)','After Disp (nm)','Reduction (%)'};

rmsData = [ ...
    round(RMS_base_acc(:),3), ...
    round(RMS_isolated_acc(:),3), ...
    round(red_acc(:),3), ...
    round(RMS_base_disp(:),3), ...
    round(RMS_isolated_disp(:),3), ...
    round(red_disp(:),3) ];

rmsCell = [ band_names(:), num2cell(rmsData) ];

% — Ensure path/file name are clean again —
filePath = strtrim(char(filePath));
name     = strtrim(char(name));
name     = regexprep(name,'[^\w\-.]','_');

rmsXlsx = fullfile(filePath, sprintf('%s_rms_summary.xlsx', name));
try
    writecell([rmsHeader; rmsCell], rmsXlsx);
catch ME
    warning('写入失败：%s\n-> %s\n改为写到当前目录。', rmsXlsx, ME.message);
    rmsXlsx = fullfile(pwd, sprintf('%s_rms_summary.xlsx', name));
    writecell([rmsHeader; rmsCell], rmsXlsx);
end
fprintf('RMS summary saved: %s\n', rmsXlsx);