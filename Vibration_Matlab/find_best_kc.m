%% ===== 全局设定与参数设置 =====
clc; clear; close all;

% 基础参数
M = 12.6;                % 载荷质量 (kg)
g = 9.81;                % 重力加速度 (m/s^2)
L_Tower = 0.46;          % 塔架长度 (m)
f0_target = 1.1;         % 目标固有频率 (Hz)

% 材料属性：黄铜
G = 77.5e9;              % 剪切模量 (Pa)
rho = 7955;              % 密度 (kg/m^3)
sigma_b = 630e6;         % 抗拉屈服强度 (Pa)

% 搜索范围
d_wire_range = 1e-3:1e-3:5e-3;       % 线径
d_in_range   = 5e-3:1e-3:9.5e-2;     % 内径
d_hook_range = 1e-3:1e-3:5e-3;       % 钩部长度
r_hook_range = 3e-3:1e-3:10e-3;      % 钩部半径

% 初始化变量
results = [];
best_freq = Inf;
best_params = [];

% 弹簧参数迭代搜索
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
    if d_out > 0.1, continue; end

    k_target = M * (2 * pi * f0_target)^2;
    n_calc = (G * d_wire^4) / (8 * D^3 * k_target);
    n_eff_options = unique(round([n_calc+1.5, n_calc+2, n_calc+2.2]));
    
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
        if L_eq > 0.35, continue; end

        L0 = n_total * d_wire + 2 * d_hook + 2 * r_hook;
        L_total = L_eq + L_Tower/2;
        f0_radial = sqrt(g / L_total) / (2*pi);

        F_max = m_eq * g;
        Kw = (4*c_index - 1)/(4*c_index - 4) + 0.615/c_index;
        tau_e = Kw * (8 * F_max * D) / (pi * d_wire^3);
        if tau_e > 0.45 * sigma_b, continue; end

        kappa3 = (4 * c_index^2 - c_index - 1)/(4 * c_index * (c_index - 1));
        kappa3_p = kappa3 + 1/(4 * c_index);
        sigma_max = kappa3_p * (16 * D * F_max) / (pi * d_wire^3);
        if sigma_max > 0.7 * sigma_b, continue; end

        actual_freq = sqrt(k_actual/m_eq)/(2*pi);

        results = [results;
            d_wire*1e3, d_in*1e3, d_out*1e3, D*1e3, ...
            c_index, n_total, n_eff, d_wire*1e3, ...
            n_total*d_wire*1e3, L_eq*1e3, A_coil*1e6, ...
            m_s, m_eq, k_actual, actual_freq, ...
            tau_e/1e6, f0_radial, sigma_max/1e6];

        if actual_freq < f0_target && actual_freq < best_freq
            best_freq = actual_freq;
            best_params = [d_wire, D, n_total, n_eff, m_s, m_eq, k_actual, ...
                actual_freq, f0_radial, sigma_max];
        end
    end
end
end
end
end
%% ===== 阻尼优化（根据最优弹簧参数） =====
if isempty(best_params)
    error('未找到满足约束的弹簧设计参数，终止执行。');
end

k_actual = best_params(7);
m_eq = best_params(6);
fn = best_params(8);
wn = 2*pi*fn;

% 阻尼搜索区间
c_range = linspace(0.1, 1000, 10000);
f_range = 0:0.1:100;
omega_range = 2 * pi * f_range;

min_T_energy = Inf;
best_T = [];
T_energy_values = zeros(size(c_range));
zeta_values = zeros(size(c_range));
C_critical = 2 * sqrt(k_actual * m_eq);

for idx = 1:length(c_range)
    c = c_range(idx);
    zeta = c / C_critical;
    zeta_values(idx) = zeta;

    T = zeros(size(omega_range));
    for j = 1:length(omega_range)
        omega = omega_range(j);
        r = omega / wn;
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

% 输出最优结果
fprintf('\n=== Optimal Damping Parameters ===\n');
fprintf('Best Damping Coefficient c = %.2f N·s/m\n', best_c);
fprintf('Corresponding Damping Ratio ζ = %.4f\n', best_zeta);
fprintf('Minimum Peak Transmission Ratio = %.4f\n', min_peak_T);
fprintf('Minimum Avg Transmission Ratio = %.4f\n', min_avg_T);
fprintf('Minimum Energy (0–100 Hz) = %.4f\n', min_T_energy);
%% ===== 多CSV文件 PSD/LPSD/RMS 批处理分析 =====
% 通用设定
gain = 100;
sens_g_per_V = 1.026;
remove_dc = true;
zero_time_start = true;
g0 = 9.81;

% 分析频带
band_edges = [1, 40; 40, 100; 1, 100];
band_names = {'[1–40] Hz', '[40–100] Hz', '[1–100] Hz'};

% 设置字体与绘图格式
fontEN = 'Arial';
set(0,'defaultAxesFontName',fontEN);
set(0,'defaultTextInterpreter','none');
set(0,'defaultLegendInterpreter','none');
set(0,'defaultAxesTickLabelInterpreter','none');

% 文件读取
[files, path] = uigetfile('*.csv', ...
    'Select one or more CSV files (first 4 lines are headers: time(s), voltage(V))', ...
    'MultiSelect','on');
if isequal(files,0), error('Selection canceled'); end
if ischar(files), files = {files}; end

numFiles = numel(files);
colors = lines(max(numFiles, 7));
markers = {'-','--',':','-.'};

% 图框初始化
figT = figure('Name','Time-Domain Acceleration (g)', 'ToolBar','none'); axT = axes(figT); hold(axT,'on'); grid(axT,'on');
figPSD  = figure('Name','Acceleration PSD', 'ToolBar','none'); ax1 = axes(figPSD); hold(ax1,'on'); grid(ax1,'on');
figLPSD = figure('Name','Acceleration LPSD', 'ToolBar','none'); ax2 = axes(figLPSD); hold(ax2,'on'); grid(ax2,'on');
figDLPSD = figure('Name','Displacement LPSD', 'ToolBar','none'); ax3 = axes(figDLPSD); hold(ax3,'on'); grid(ax3,'on');

set([ax1, ax2, ax3],'XScale','log','YScale','log');
xlabel(ax1,'Frequency (Hz)'); ylabel(ax1,'PSD [g^2/Hz]');
xlabel(ax2,'Frequency (Hz)'); ylabel(ax2,'LPSD [g/sqrt(Hz)]');
xlabel(ax3,'Frequency (Hz)'); ylabel(ax3,'LPSD [nm/sqrt(Hz)]');

title(ax1,'Acceleration PSD'); title(ax2,'Acceleration LPSD'); title(ax3,'Displacement LPSD');
xlabel(axT,'Time (s)'); ylabel(axT,'Acceleration (g)'); title(axT,'Time-Domain Acceleration (g)');

% 初始化变量
legNames = cell(1, numFiles);
fileLabels = cell(numFiles,1);
allRMS_acc = cell(numFiles,1);
allRMS_disp = cell(numFiles,1);
allFreqMax = zeros(numFiles,1);
maxDuration = 0;

% 主循环处理每个CSV文件
for k = 1:numFiles
    infile = fullfile(path, files{k});
    [~, nameOnly] = fileparts(files{k});
    nameSafe = regexprep(nameOnly, '[^\w\-.]', '_');
    fileLabels{k} = nameSafe;

    opts = detectImportOptions(infile, 'NumHeaderLines', 4);
    M = readmatrix(infile, opts);
    if size(M,2) < 2
        warning('File %s has insufficient columns and will be skipped.', files{k});
        continue;
    end
    t_raw = M(:,1); v_raw = M(:,2);
    [t_raw, idx] = sort(t_raw(:));
    v_raw = v_raw(idx);

    acc_g = v_raw ./ (gain * sens_g_per_V);
    if remove_dc, acc_g = acc_g - mean(acc_g, 'omitnan'); end
    if zero_time_start
    t = t_raw - t_raw(1);
    else
        t = t_raw;
    end

    % 时域图
    styleID = mod(k-1, numel(markers)) + 1;
    plot(axT, t, acc_g, 'LineWidth', 1.2, 'Color', colors(k,:), 'LineStyle', markers{styleID});
    legNames{k} = sprintf('%s (g)', nameSafe);
    if ~isempty(t), maxDuration = max(maxDuration, t(end)); end

    % 频域参数
    dt = median(diff(t));
    fs = 1/dt;
    N = numel(acc_g);
    seg_target = max(1024, floor(N/4));
    seglen = max(512, min(2^floor(log2(seg_target)), N));
    nfft = max(2^nextpow2(seglen), 1024);
    win = hamming(seglen);
    overlap = round(0.5 * seglen);

    [pxx_g, f] = pwelch(acc_g(:), win, overlap, nfft, fs);
    df = mean(diff(f));
    f = f(f > 0); pxx_g = pxx_g(1:length(f));
    allFreqMax(k) = max(f);

    % LPSD 和位移
    lpsd_acc_g = sqrt(pxx_g);
    lpsd_acc_ms2 = lpsd_acc_g * g0;
    lpsd_disp_m  = lpsd_acc_ms2 ./ ((2*pi*f).^2);
    lpsd_disp_nm = lpsd_disp_m * 1e9;

    % RMS分析
    RMS_acc_g = zeros(size(band_edges,1),1);
    RMS_disp_m = zeros(size(band_edges,1),1);
    for ib = 1:size(band_edges,1)
        f1 = band_edges(ib,1); f2 = band_edges(ib,2);
        idx = (f >= f1) & (f <= f2);
        if nnz(idx) < 2
            RMS_acc_g(ib) = NaN;
            RMS_disp_m(ib) = NaN;
        else
            RMS_acc_g(ib)  = sqrt(sum((lpsd_acc_g(idx)).^2) * df);
            RMS_disp_m(ib) = sqrt(sum((lpsd_disp_m(idx)).^2) * df);
        end
    end
    allRMS_acc{k} = RMS_acc_g;
    allRMS_disp{k} = RMS_disp_m;

    % 绘图
    plot(ax1, f, pxx_g, 'Color', colors(k,:), 'LineStyle', markers{styleID}, 'LineWidth', 1.5, 'DisplayName', nameSafe);
    plot(ax2, f, lpsd_acc_g, 'Color', colors(k,:), 'LineStyle', markers{styleID}, 'LineWidth', 1.5, 'DisplayName', nameSafe);
    plot(ax3, f, lpsd_disp_nm, 'Color', colors(k,:), 'LineStyle', markers{styleID}, 'LineWidth', 1.5, 'DisplayName', nameSafe);
end

% 图例与坐标轴统一
legend(axT, legNames, 'Interpreter','none','Location','best');
if maxDuration > 0, xlim(axT, [0, maxDuration]); end
xlim(ax1, [1, max(allFreqMax)]); xlim(ax2, [1, max(allFreqMax)]); xlim(ax3, [1, max(allFreqMax)]);
legend(ax1, 'show'); legend(ax2, 'show'); legend(ax3, 'show');
%% ===== 输出 RMS Summary 表格（ug / nm 单位） =====
rms_cell = cell(numFiles, 1+3+3);
for i = 1:numFiles
    rms_cell{i,1} = fileLabels{i};
    Ra = allRMS_acc{i}; Rd = allRMS_disp{i};
    for ib = 1:3
        if ~isempty(Ra) && ~isnan(Ra(ib))
            rms_cell{i,1+ib} = sprintf('%.2f ug', Ra(ib)*1e6);
        else
            rms_cell{i,1+ib} = 'N/A';
        end
        if ~isempty(Rd) && ~isnan(Rd(ib))
            rms_cell{i,1+3+ib} = sprintf('%.2f nm', Rd(ib)*1e9);
        else
            rms_cell{i,1+3+ib} = 'N/A';
        end
    end
end

figTbl = figure('Name','RMS Summary Table','Units','pixels','Color','w', 'ToolBar','none');
col_names = {'Filename', '[1–40Hz] Acc.', '[40–100Hz] Acc.', '[1–100Hz] Acc.', ...
                        '[1–40Hz] Disp.', '[40–100Hz] Disp.', '[1–100Hz] Disp.'};
uitable('Parent', figTbl, ...
    'Data', rms_cell, ...
    'ColumnName', col_names, ...
    'Units','normalized', ...
    'Position',[0.05 0.05 0.9 0.9], ...
    'FontSize', 10, ...
    'FontName','Microsoft YaHei', ...
    'RowName', []);
set(figTbl, 'Position', [100, 100, 900, min(500, 100 + 28*numFiles)]);
%% ===== 显示最佳弹簧 + 阻尼器参数 =====
spring_material = 'Brass';
d_wire = best_params(1);
D = best_params(2);
n_eff = best_params(4);
L0 = n_eff * d_wire;
k_actual = best_params(7);

spring_data = {
    spring_material, ...
    d_wire*1000, ...   % mm
    D*1000, ...        % mm
    n_eff, ...         % 圈数
    L0, ...            % m
    k_actual, ...      % N/m
    best_c             % Ns/m
};

spring_header = {'Material', 'Wire Diameter (mm)', 'Mean Diameter (mm)', ...
                 'Effective Turns', 'Original Length (m)', 'Stiffness (N/m)', 'Damping Coefficient (N·s/m)'};

figSpring = figure('Name','Optimal Spring Design','Units','inches','Position',[1 1 10 2.5]);
uitable(figSpring, ...
    'Data', spring_data, ...
    'ColumnName', spring_header, ...
    'Units','normalized', ...
    'Position',[0.05 0.2 0.9 0.6], ...
    'FontSize', 11, ...
    'RowName', []);
