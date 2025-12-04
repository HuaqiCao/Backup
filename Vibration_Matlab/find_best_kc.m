%% ============================================================
% 1）弹簧设计：通过材料力学 + 疲劳极限 + 几何约束搜索最优弹簧参数
% 2）阻尼优化：搜索最优阻尼系数 c，使传递率能量最小
% 3）真实加速度数据隔振：频域滤波模拟隔振后的加速度
% 4）绘图：传递率曲线、能量 vs 阻尼、频响、PSD、LPSD、时间域对比
% 5）输出：最佳弹簧参数 + 最优 c + RMS 结果写入 Excel
%% ============================================================


% === 基础参数：载荷质量、材料属性、目标固有频率 ===
M = 12.6;                % 负载质量 (kg)
g = 9.81;                % 重力加速度 (m/s^2)

% 材料参数：304 不锈钢
G = 77.5e9;              % 剪切模量 (Pa)
rho = 7955;              % 密度 (kg/m^3)
sigma_b = 630e6;         % 抗拉屈服极限 (Pa)

% 目标竖直固有频率
f0_vertical = 1.1;                  
k_target = M * (2 * pi * f0_vertical)^2;
L_Tower = 0.46;          % 结构尺寸约束（塔高）

% === 搜索变量空间：线径、内径、钩直径、钩半径 ===
d_wire_range = 1e-3:1e-3:5e-3;
d_in_range   = 5e-3:1e-3:9.5e-2;
d_hook_range = 1e-3:1e-3:5e-3;
r_hook_range = 3e-3:1e-3:10e-3;

% === 预分配存储空间（避免循环中扩展数组）===
maxRows = numel(d_wire_range) * numel(d_in_range) * numel(d_hook_range) * numel(r_hook_range) * 3;
results = nan(maxRows, 18);
res_count = 0;

best_freq   = Inf;         
best_params = [];
best_L0     = NaN;
material_name = 'Stainless Steel';

% ==============================================================  
% === 主循环：搜索符合力学 + 疲劳 + 尺寸 + 自振频率的弹簧参数 ===
% ==============================================================  
for i = 1:length(d_wire_range)
    for j = 1:length(d_in_range)
        for m = 1:length(d_hook_range)
            for n = 1:length(r_hook_range)

                % === 基本几何计算 ===
                d_wire = d_wire_range(i);
                d_in   = d_in_range(j);
                d_hook = d_hook_range(m);
                r_hook = r_hook_range(n);

                d_out = d_in + 2 * d_wire;
                D = (d_in + d_out) / 2;
                c_index = D / d_wire;      % 形状系数

                if d_out > 0.1
                    continue;
                end

                % === 根据刚度反推有效圈数 ===
                n_calc = (G * d_wire^4) / (8 * D^3 * k_target);
                n_eff_options = unique(round([n_calc+1.5, ceil(n_calc), ceil(n_calc)+1]));

                % === 逐个圈数尝试 ===
                for k = 1:length(n_eff_options)
                    n_eff = n_eff_options(k);
                    n_total = n_eff + 2;          % 总圈数 = 有效圈 + 两端支撑

                    % === 实际刚度 ===
                    k_actual = (G * d_wire^4) / (8 * D^3 * n_eff);

                    % === 线材长度 + 自重等效质量 ===
                    A_coil = pi * (d_wire^2 / 4);
                    L_wire = n_eff * pi * D;
                    m_s = rho * A_coil * L_wire;  
                    m_eq = M + (1/3) * m_s;

                    % === 静挠度 + 自由长度 ===
                    delta_static = m_eq * g / k_actual;
                    L_eq = n_total * d_wire + delta_static + 2 * d_hook + 2 * r_hook;
                    if L_eq > 0.35
                        continue;
                    end
                    L0 = n_total * d_wire + 2 * d_hook + 2 * r_hook;
                    L = L_eq + L_Tower * 2 / 5;
                    pitch = (L0 - 2 * d_hook - 2 * r_hook) / n_eff;

                    % === 横向固有频率（结构限值）===
                    f0_radial = sqrt(g / L) / (2 * pi);

                    % === 等效应力：Wahl 因子 ===
                    F_max = m_eq * g;
                    Kw = (4*c_index - 1)/(4*c_index -4) + 0.615/c_index;
                    tau_e = Kw * (8 * F_max * D) / (pi * d_wire^3);

                    if tau_e > 0.45 * sigma_b 
                        continue;         
                    end

                    % === 最大拉应力（疲劳约束）===
                    kappa_3 = (4*c_index^2 - c_index - 1) / (4*c_index * (c_index - 1));
                    kappa_3_prime = kappa_3 + 1 / (4*c_index);
                    sigma_max = kappa_3_prime * (16 * D * F_max) / (pi * d_wire^3);

                    if sigma_max >= 0.7 * sigma_b
                        continue;
                    end

                    % === 真实固有频率（目标 < 1.1 Hz）===
                    actual_freq = sqrt(k_actual/m_eq)/(2*pi);

                    % === 保存候选 ===
                    res_count = res_count + 1;
                    results(res_count, :) = [ ...
                      d_wire*1000, d_in*1000, d_out*1000, D*1000, ...
                      c_index, n_total, n_eff, pitch*1000, ...
                      L0*1000, L_eq*1000, A_coil*1e6, ...
                      m_s, m_eq, k_actual, ...
                      actual_freq, ...
                      tau_e/1e6, f0_radial, sigma_max/1e6];

                    % === 更新最优解 ===
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

% === 去除空行 ===
results = results(1:res_count, :);


% ==============================================================  
% === 输出所有满足条件的设计结果 ===
% ==============================================================  
if ~isempty(results)
    header = {'Wire_d_mm','Inner_d_mm','Outer_d_mm','Mean_D_mm','Index_c',...
        'Total_turns','Eff_turns','Pitch_mm','Free_len_L0_mm',...
        'Assembly_len_Leq_mm','Area_mm2','Spring_mass_kg',...
        'Eff_mass_kg','Stiffness_N_m','Freq_Hz',...
        'Tau_max_MPa','Radial_freq_Hz','Sigma_max_MPa'};
    
    fprintf('\n=== 满足要求的弹簧设计 ===\n');
    fprintf('%-10s %-10s %-10s %-10s %-10s %-10s %-10s %-10s %-10s %-10s %-10s %-12s %-12s %-10s %-10s %-12s %-10s %-10s\n', header{:});
    
    for i = 1:size(results,1)
        fprintf('%-10.2f %-10.2f %-10.2f %-10.2f %-10.2f %-10d %-10d %-10.2f %-10.2f %-10.2f %-10.2f %-12.4f %-12.4f %-10.1f %-10.2f %-12.2f %-10.2f %-10.2f\n', results(i,:));
    end

    % === 输出最优弹簧设计 ===
    if ~isempty(best_params)
        fprintf('\n=== Optimal Spring Design（最佳弹簧方案）===\n');
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


% ==============================================================  
% === 阻尼优化（搜索最佳 c，最小化传递能量）===
% ==============================================================  
k_actual = best_params(7);
m_eq     = best_params(6);
fn       = best_params(8);
wn       = 2*pi*fn;

% === 定义阻尼范围、频率范围 ===
c_range     = linspace(0.1, 1000, 10000);
f_range     = 0:0.1:1000;
omega_range = 2*pi*f_range;

best_c = 0;
min_T_energy = Inf;
best_T = [];

T_energy_values = zeros(size(c_range));
zeta_values     = zeros(size(c_range));

C_constant = 2*sqrt(k_actual*m_eq);

% === 遍历阻尼系数并计算 T(ω) 能量 ===
for idx = 1:length(c_range)
    c = c_range(idx);
    zeta = c / C_constant;
    zeta_values(idx) = zeta;

    % === 单自由度传递率 ===
    T = zeros(size(omega_range));
    for j = 1:length(omega_range)
        omega = omega_range(j);
        r = omega/wn;
        numerator   = sqrt(1 + (2*zeta*r)^2);
        denominator = sqrt((1 - r^2)^2 + (2*zeta*r)^2);
        T(j) = numerator / denominator;
    end

    % === 计算 T² 的能量积分 ===
    T_energy = trapz(f_range, T.^2);
    T_energy_values(idx) = T_energy;

    if T_energy < min_T_energy
        min_T_energy = T_energy;
        min_peak_T   = max(T);
        min_avg_T    = mean(T);
        best_c   = c;
        best_T   = T;
        best_zeta= zeta;
    end
end

% === 输出最优阻尼参数 ===
fprintf('\n=== Optimal Damping Parameters ===\n');
fprintf('Best Damping Coefficient c = %.2f N·s/m\n', best_c);
fprintf('Corresponding Damping Ratio ζ = %.4f\n', best_zeta);
fprintf('Minimum Peak Transmission Ratio = %.4f\n', min_peak_T);
fprintf('Minimum Avg Transmission Ratio = %.4f\n', min_avg_T);
fprintf('Minimum Energy (0–1000 Hz) = %.4f\n', min_T_energy);


% ==============================================================  
% === 将最优弹簧参数写入 Excel ===
% ==============================================================  
if exist('filePath','var') ~= 1
    filePath = pwd;
    name = char(datetime('now','Format','yyyyMMdd_HHmmss'));
end

springHeader = {'Material','Wire Diameter (mm)','Mean Diameter (mm)', ...
                'Effective Turns','Original Length (m)', ...
                'Stiffness (N/m)','Damping Coefficient (N·s/m)'};
springRow = { ...
    material_name, ...
    round(best_params(1)*1000,2), ...
    round(best_params(2)*1000,2), ...
    best_params(4), ...
    round(best_L0,4), ...
    round(best_params(7),2), ...
    round(best_c,2) };

springXlsx = fullfile(filePath, sprintf('%s_best_spring.xlsx', name));
try
    writecell([springHeader; springRow], springXlsx);
catch ME
    warning('写入失败：%s\n改写入当前目录。', ME.message);
    springXlsx = fullfile(pwd, sprintf('%s_best_spring.xlsx', name));
    writecell([springHeader; springRow], springXlsx);
end
fprintf('Best spring parameters saved: %s\n', springXlsx);


% ==============================================================  
% === 设置全局绘图字体 ===
% ==============================================================  
fontEN = 'Arial';
set(0,'defaultAxesFontName',fontEN);
set(0,'defaultTextFontName',fontEN);
set(0,'defaultLegendFontName',fontEN);
set(0,'defaultUIControlFontName',fontEN);
set(0,'defaultAxesFontSize',12);

figSize = [1, 1, 10, 5];


% ==============================================================  
% === 频响曲线图（传递率 vs 频比）===
% ==============================================================  
figure('Name','Transmission Ratio Curve','Units','inches','Position',figSize);
r_range = omega_range / wn;

plot(r_range, best_T, 'b-', 'LineWidth', 2); hold on;
plot([1,1], [0,max(best_T)], 'r--', 'LineWidth', 1.5);
plot([sqrt(2),sqrt(2)], [0,max(best_T)], 'g--', 'LineWidth', 1.5);
xlabel('Frequency Ratio (r = \omega/\omega_n)');
ylabel('Transmission Ratio T');
title('Frequency Response Curve','FontSize',24);
grid on;
xlim([0,5]);


% ==============================================================  
% === 能量 vs 阻尼系数 ===
% ==============================================================  
figure('Name','Energy vs Damping Coefficient','Units','inches','Position',figSize);
semilogx(c_range, T_energy_values, 'b-', 'LineWidth', 2); hold on;
plot([best_c best_c], [min(T_energy_values),max(T_energy_values)], 'r--', 'LineWidth',1.5);
xlabel('Damping Coefficient c (N·s/m)');
ylabel('Transmission Energy');
title('Energy vs. Damping Coefficient','FontSize',24);
grid on;


% ==============================================================  
% === 能量 vs 阻尼比 ===
% ==============================================================  
figure('Name','Energy vs Damping Ratio','Units','inches','Position',figSize);
plot(zeta_values, T_energy_values, 'b-', 'LineWidth',2); hold on;
plot([best_zeta best_zeta], [min(T_energy_values),max(T_energy_values)], 'r--', 'LineWidth',1.5);
xlabel('Damping Ratio \zeta');
ylabel('Transmission Energy');
title('Energy vs. Damping Ratio','FontSize',24);
grid on;


% ==============================================================  
% === 原始加速度 CSV：读取并进行隔振处理（频域滤波）===
% ==============================================================  
[fileName, filePath] = uigetfile('*.csv', 'Select Source Acceleration CSV File');
if isequal(fileName, 0), error('User canceled file selection.'); end

% === 读取前 4 行标题 ===
fid = fopen(fullfile(filePath,fileName),'r');
headerLines = cell(4,1);
for i=1:4, headerLines{i}=fgetl(fid); end
fclose(fid);

% === 读取数据 ===
opts = detectImportOptions(fullfile(filePath,fileName),'NumHeaderLines',4);
data = readmatrix(fullfile(filePath,fileName), opts);
time = data(:,1);
voltage = data(:,2);

% 传感器转换到 SI 单位加速度
gain = 100;
sens_V_per_g = 1.026;
g0 = 9.80665;

acc_base_g = voltage / (gain * sens_V_per_g);
acc_base = acc_base_g * g0;
acc_base = acc_base - mean(acc_base);

dt = median(diff(time));
fs = 1/dt;
N  = length(time);

% === 全频 FRF 对齐 FFT ===
k = (0:(N-1)).';
omega_full = 2*pi*fs * (k/N);
s = 1i * omega_full;
H_full = (best_c*s + k_actual) ./ (m_eq*(s.^2) + best_c*s + k_actual);

fft_base = fft(acc_base(:));
fft_isolated = fft_base .* H_full;

acc_isolated = real(ifft(fft_isolated,'symmetric'));
acc_isolated = acc_isolated - mean(acc_isolated);


% ==============================================================  
% === 时间域隔振对比图 ===
% ==============================================================  
figure('Name','Time-Domain Comparison','Units','inches','Position',figSize);
plot(time, acc_base_g, 'b-', 'LineWidth',1.5); hold on;
plot(time, acc_isolated/g0, 'r-', 'LineWidth',1.5);
legend('Before Isolation','After Isolation');
xlabel('Time (s)'); ylabel('Acceleration (g)');
title('Time-Domain Comparison'); grid on;


% ==============================================================  
% === 输出隔振后的 CSV（保持原前 4 行格式）===
% ==============================================================  
acc_isolated_g = acc_isolated / g0;
voltage_isolated = acc_isolated_g * sens_V_per_g * gain;

[~, name, ext] = fileparts(fileName);
outputFileName = fullfile(filePath, [name '_isolated' ext]);

fid = fopen(outputFileName,'w');
for i=1:4, fprintf(fid,'%s\n',headerLines{i}); end
for i=1:length(time)
    fprintf(fid,'%.6f,%.6f\n', time(i), voltage_isolated(i));
end
fclose(fid);

fprintf('Isolated acceleration saved: %s\n', outputFileName);


% ==============================================================  
% === PSD 与 LPSD 分析（加速度/位移/频带 RMS）===
% ==============================================================  
seglen  = min(round(fs*10), N);
window  = hamming(seglen,'periodic');
overlap = round(seglen/2);
nfft    = seglen;

[Sa_base, f] = pwelch(acc_base, window, overlap, nfft, fs,'psd');
[Sa_isolated,~] = pwelch(acc_isolated, window, overlap, nfft, fs,'psd');

% === Parseval 检查（验证 PSD 是否正确）===
var_time = var(acc_base);
var_freq = trapz(f,Sa_base);

% === 有效频率范围 (f>=1Hz) ===
pos = f >= 1;

% === 加速度 LPSD（g/√Hz）===
lpsd_base = zeros(size(f));
lpsd_isolated = zeros(size(f));
lpsd_base(pos) = sqrt(Sa_base(pos))/g0;
lpsd_isolated(pos) = sqrt(Sa_isolated(pos))/g0;

% === 位移 LPSD（nm/√Hz）===
w = 2*pi*f;
lpsd_base_disp = zeros(size(f));
lpsd_iso_disp  = zeros(size(f));
lpsd_base_disp(pos) = (sqrt(Sa_base(pos))./(w(pos).^2)) * 1e9;
lpsd_iso_disp(pos)  = (sqrt(Sa_isolated(pos))./(w(pos).^2)) * 1e9;


% ==============================================================  
% === RMS 计算（加速度 μg，位移 nm）===
% ==============================================================  
band_edges = [1,40; 40,1000; 1,1000];
band_names = {'[1–40] Hz','(40–1k] Hz','[1–1k] Hz'};
nBands = size(band_edges,1);

Sd_base     = Sa_base ./ (w.^4);
Sd_isolated = Sa_isolated ./ (w.^4);

RMS_base_acc = zeros(1,nBands);
RMS_isolated_acc = zeros(1,nBands);
RMS_base_disp = zeros(1,nBands);
RMS_isolated_disp = zeros(1,nBands);

for iBand = 1:nBands
    lo = band_edges(iBand,1);
    hi = band_edges(iBand,2);

    if iBand==1
        idx = (f>=lo)&(f<hi)&pos;
    elseif iBand==nBands
        idx = (f>=lo)&(f<=hi)&pos;
    else
        idx = (f>lo)&(f<=hi)&pos;
    end

    RMS_base_acc_SI = sqrt(trapz(f(idx), Sa_base(idx)));
    RMS_iso_acc_SI  = sqrt(trapz(f(idx), Sa_isolated(idx)));
    RMS_base_disp_m = sqrt(trapz(f(idx), Sd_base(idx)));
    RMS_iso_disp_m  = sqrt(trapz(f(idx), Sd_isolated(idx)));

    RMS_base_acc(iBand)     = (RMS_base_acc_SI / g0)*1e6;
    RMS_isolated_acc(iBand) = (RMS_iso_acc_SI / g0)*1e6;
    RMS_base_disp(iBand)    =  RMS_base_disp_m * 1e9;
    RMS_isolated_disp(iBand)=  RMS_iso_disp_m * 1e9;
end

fprintf('\n=== RMS Summary ===\n');
MU = char(956);
fprintf('%-16s %-14s %-14s %-22s | %-14s %-14s %-22s\n', ...
    'Band',['Base(' MU 'g)'],['Iso(' MU 'g)'],'Change%',...
    'Base(nm)','Iso(nm)','Change%');

for iBand = 1:nBands
    dA = (RMS_isolated_acc(iBand)-RMS_base_acc(iBand))./RMS_base_acc(iBand)*100;
    dD = (RMS_isolated_disp(iBand)-RMS_base_disp(iBand))./RMS_base_disp(iBand)*100;

    fprintf('%-16s %-12.2f %-12.2f %-10.2f | %-12.2f %-12.2f %-10.2f\n',...
        band_names{iBand},RMS_base_acc(iBand),RMS_isolated_acc(iBand),dA,...
        RMS_base_disp(iBand),RMS_isolated_disp(iBand),dD);
end


% ==============================================================  
% === 输出 RMS 到 Excel ===
% ==============================================================  
rmsHeader = { 'Frequency Band', ['Before Acc (' MU 'g)'], ['After Acc (' MU 'g)'],...
              'Change%','Before Disp (nm)','After Disp (nm)','Change%' };

chg_acc = (RMS_isolated_acc-RMS_base_acc)./RMS_base_acc*100;
chg_disp= (RMS_isolated_disp-RMS_base_disp)./RMS_base_disp*100;

rmsData = [ ...
    round(RMS_base_acc(:),3),...
    round(RMS_isolated_acc(:),3),...
    round(chg_acc(:),3),...
    round(RMS_base_disp(:),3),...
    round(RMS_isolated_disp(:),3),...
    round(chg_disp(:),3) ];

rmsCell = [band_names(:), num2cell(rmsData)];

rmsXlsx = fullfile(filePath, sprintf('%s_rms_summary.xlsx', name));
writecell([rmsHeader; rmsCell], rmsXlsx);

fprintf('RMS summary saved: %s\n', rmsXlsx);
