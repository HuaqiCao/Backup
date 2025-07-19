function spring_design_analysis()
%% === 1. 文件选择 ===
[fileName, filePath] = uigetfile('*.csv', '选择加速度 CSV 文件');
if isequal(fileName, 0)
    error('❌ 用户取消了文件选择。');
end
fullFileName = fullfile(filePath, fileName);

%% === 2. 读取数据 ===
opts = detectImportOptions(fullFileName, 'NumHeaderLines', 4);
data = readmatrix(fullFileName, opts);
time = data(:,1);
sensitivity = 1.026; % V/g
gain = 100;         
voltage = data(:,2);
voltage = voltage - mean(voltage);  % 去除偏置
a_base = voltage / (sensitivity * gain);  % 转换为加速度 [g]

%% === 3. PSD 参数 ===
dt = mean(diff(time));
fs = 1 / dt;
nfft = 100000;
window = hanning(nfft);
overlap = round(0.5 * nfft);
[pxx, f] = pwelch(a_base, window, overlap, nfft, fs);
w = 2 * pi * f;

%% === 3.1 加速度 - 速度 - 位移 LPSD 计算 ===
sensitivity = 1.026; 
g = 9.81;
lpsd_acc = sqrt(pxx);                 
lpsd_vel = g ./ (2*pi*f) .* lpsd_acc;
lpsd_disp = g ./ ((2*pi*f).^2) .* lpsd_acc;

source_lpsd_acc = lpsd_acc;
source_lpsd_disp = lpsd_disp;

%% === 3.2 RMS 计算 ===
band_edges = [1, 40; 40, 100; 1, 100];
df = mean(diff(f));
RMS_result = zeros(size(band_edges,1), 2);
for i = 1:size(band_edges,1)
    idx = f >= band_edges(i,1) & f <= band_edges(i,2);
    rms_acc = sqrt(sum((lpsd_acc(idx).^2) * df));
    rms_disp = sqrt(sum((lpsd_disp(idx).^2) * df));
    RMS_result(i, :) = [rms_acc, rms_disp*1e9];
end
source_RMS = RMS_result;

%% === 4. 目标频段与载荷质量 ===
M = 12.6;
g = 9.81;
f_band = [1, 100];
f_idx = f >= f_band(1) & f <= f_band(2);
f_opt = f(f_idx);
pxx_opt = pxx(f_idx);

%% === 5. 材料属性 ===
G = 77e9;
rho = 7930;
sigma_b = 505e6;

%% === 6. 搜索范围 ===
d_wire_range = 1e-3:1e-3:5e-3;
d_in_range = 5e-3:1e-3:9.5e-2;
d_hook_range = 1e-3:1e-3:5e-3;
r_hook_range = 2e-3:1e-3:8e-3;

best_ratio = inf;
best_c = NaN;
best_H = [];
best_params = [];

results = [];

for i = 1:length(d_wire_range)
    for j = 1:length(d_in_range)
        for m = 1:length(d_hook_range)
            for n = 1:length(r_hook_range)
                d_wire = d_wire_range(i);
                d_in = d_in_range(j);
                d_hook = d_hook_range(m);
                r_hook = r_hook_range(n);

                d_out = d_in + 2 * d_wire;
                D = (d_in + d_out) / 2;
                c_index = D / d_wire;
                if d_out > 0.1
                    continue;
                end

                f0_vertical = 1.3;
                k_target = M * (2 * pi * f0_vertical)^2;
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
                    f0_vertical_actual = sqrt(k_actual / m_eq) / (2 * pi);  

                    delta_static = m_eq * g / k_actual;
                    L_eq = n_total * d_wire + delta_static + 2 * d_hook + 2 * r_hook;
                    if L_eq > 0.33
                        continue;
                    end

                    f0_radial = sqrt(g / L_eq) / (2 * pi);
                    F_max = m_eq * g;
                    Kw = (4*c_index - 1)/(4*c_index - 4) + 0.615/c_index;
                    tau_e = Kw * (8 * F_max * D) / (pi * d_wire^3);
                    FOS_e = sigma_b / tau_e;
                    if FOS_e < 1/0.45
                        continue;
                    end

                    kappa_3 = (4 * c_index^2 - c_index - 1) / (4 * c_index * (c_index - 1));
                    kappa_3_prime = kappa_3 + 1 / (4 * c_index);
                    sigma_max = kappa_3_prime * (16 * D * F_max) / (pi * d_wire^3);
                    if sigma_max >= 0.7 * sigma_b
                        continue;
                    end

                    wn = sqrt(k_actual / m_eq);
                    c_range = linspace(0, 1000, 2);
                    for c = c_range
                        zeta = c / (2 * sqrt(k_actual * m_eq));
                        r_opt = f_opt / wn;
                        H_opt = sqrt((1 + 4 * zeta.^2 .* r_opt.^2) ./ ((1 - r_opt.^2).^2 + 4 * zeta.^2 .* r_opt.^2));
                        pxx_out_opt = (H_opt.^2) .* pxx_opt;

                        idx_1_100 = f_opt >= 1 & f_opt <= 100;
                        rms_acc_opt = sqrt(sum((H_opt(idx_1_100).^2 .* pxx_opt(idx_1_100)) * df));

                        if rms_acc_opt < best_ratio

                            best_ratio = rms_acc_opt;
                            best_c = c;
                            r_all = f / wn;
                            zeta_all = c / (2 * sqrt(k_actual * m_eq));
                            best_H = sqrt((1 + 4 * zeta_all.^2 .* r_all.^2) ./ ((1 - r_all.^2).^2 + 4 * zeta_all.^2 .* r_all.^2));
                            best_params = [d_wire, D, n_total, n_eff, m_s, m_eq, k_actual, sqrt(k_actual/m_eq)/(2*pi), FOS_e, f0_radial, sigma_max];
                        end
                    end

                    results = [results;
                        d_wire*1000, d_in*1000, d_out*1000, D*1000, ...
                        c_index, n_total, n_eff, d_wire*1000, ...
                        n_total*d_wire*1000, L_eq*1000, A_coil*1e6, ...
                        m_s, m_eq, k_actual, sqrt(k_actual/m_eq)/(2*pi), ...
                        tau_e/1e6, FOS_e, f0_radial, sigma_max/1e6];
                end
            end
        end
    end
end

%% === 7. 计算最佳设计的LPSD ===
if ~isempty(best_H)
    best_lpsd_acc = sqrt((best_H.^2).*pxx);
    best_lpsd_disp = g ./ ((2*pi*f).^2) .* best_lpsd_acc;

    % === 计算最佳设计的RMS ===
    best_RMS = zeros(size(band_edges,1), 2);
    for i = 1:size(band_edges,1)
        idx = f >= band_edges(i,1) & f <= band_edges(i,2);
        rms_acc = sqrt(sum((best_lpsd_acc(idx).^2) * df));
        rms_disp = sqrt(sum((best_lpsd_disp(idx).^2) * df));
        best_RMS(i, :) = [rms_acc, rms_disp*1e9];
    end
end

%% === 8. 结果输出 ===
if ~isempty(results)
    header = {'线径_d_mm', '内径_din_mm', '外径_dout_mm', '中径_D_mm', '旋绕比_c', ...
        '总圈数_n_total', '有效圈数_n_eff', '节距_p_mm', '自由长度_L0_mm', ...
        '装配长度_Leq_mm', '横截面积_A_mm2', '弹簧质量_ms_kg', ...
        '等效质量_meq_kg', '刚度_k_N_m', '轴向固频_fn_Hz', ...
        '最大剪应力_tau_MPa', '疲劳安全系数_FOSf', '径向固频_fr_Hz', ...
        '最大拉应力_sigma_MPa'};

    result_table = array2table(results, 'VariableNames', header);
    disp('✅ 满足设计约束的弹簧参数:');
    disp(result_table);

    fprintf('\n=== 最佳弹簧参数 ===\n');
    fprintf('线径: %.1f mm\n', best_params(1)*1000);
    fprintf('中径: %.1f mm\n', best_params(2)*1000);
    fprintf('总圈数: %d (有效圈数: %d)\n', best_params(3), best_params(4));
    fprintf('弹簧质量: %.3f kg\n', best_params(5));
    fprintf('等效质量: %.3f kg\n', best_params(6));
    fprintf('刚度: %.1f N/m\n', best_params(7));
    fprintf('轴向固有频率: %.2f Hz\n', best_params(8));
    fprintf('疲劳安全系数: %.2f\n', best_params(9));
    fprintf('径向固有频率: %.2f Hz\n', best_params(10));
    fprintf('最大拉应力: %.2f MPa\n', best_params(11)/1e6);
    fprintf('最优阻尼: %.2f Ns/m\n', best_c);
end

%% === 9. 绘图 ===
% 1. 输入 vs 响应 PSD对比图
figure('Name','输入 vs 响应 PSD','Units','inches','Position', [1, 1, 9.59, 4.22]);
loglog(f, pxx, 'b-', 'LineWidth', 1.5, 'DisplayName', '输入加速度'); hold on;
if ~isempty(best_H)
    loglog(f, (best_H.^2).*pxx, 'r--', 'LineWidth', 1.5, 'DisplayName', '响应加速度');
end
xlabel('频率 (Hz)'); ylabel('PSD (m^2/s^3/Hz)');
title('输入 vs 响应 PSD 对比'); 
legend('Location', 'best'); grid on;

% 2. 加速度传递函数模值图
figure('Name','加速度传递函数','Units','inches','Position', [1, 1, 9.59, 4.22]);
semilogx(f, best_H, 'k-', 'LineWidth', 1.5);
xlabel('频率 (Hz)'); ylabel('加速度传递率 |H(f)|');
title('加速度传递函数模值'); grid on;

% 3. 频率响应隔振倍率图
figure('Name','功率传递率','Units','inches','Position', [1, 1, 9.59, 4.22]);
semilogx(f, best_H.^2, 'm-', 'LineWidth', 1.5);
xlabel('频率 (Hz)'); ylabel('功率传递率 |H(f)|²');
title('频率响应隔振倍率'); grid on;

% 4. 加速度LPSD对比图
figure('Name','加速度 LPSD 对比','Units','inches','Position', [1, 1, 9.59, 4.22]);
loglog(f, source_lpsd_acc, 'b-', 'LineWidth', 1.5, 'DisplayName', 'MXC振动'); hold on;
if ~isempty(best_H)
    loglog(f, best_lpsd_acc, 'r--', 'LineWidth', 1.5, 'DisplayName', '最佳设计');
end
xlabel('频率 [Hz]'); ylabel('LPSD [g/√Hz]');
title('加速度 LPSD 对比');
legend('Location', 'best');
grid on; set(gca, 'XScale', 'log', 'YScale', 'log');

% 5. 位移LPSD对比图
figure('Name','位移 LPSD 对比','Units','inches','Position', [1, 1, 9.59, 4.22]);
loglog(f, source_lpsd_disp*1e9, 'b-', 'LineWidth', 1.5, 'DisplayName', 'MXC振动'); hold on;
if ~isempty(best_H)
    loglog(f, best_lpsd_disp*1e9, 'r--', 'LineWidth', 1.5, 'DisplayName', '最佳设计');
end
xlabel('频率 [Hz]'); ylabel('LPSD [nm/√Hz]');
title('位移 LPSD 对比');
legend('Location', 'best');
grid on; set(gca, 'XScale', 'log', 'YScale', 'log');

%% === 10. RMS结果展示 ===
if ~isempty(best_H)
    % 准备表格数据
    band_names = {'MXC振动', '最佳设计'};
    col_names = {'[1-40] Hz Acc', '[40-100] Hz Acc', '[1-100] Hz Acc', ...
                 '[1-40] Hz Disp', '[40-100] Hz Disp', '[1-100] Hz Disp'};
    
    % 组合RMS数据
    rms_data = [source_RMS(1,1), source_RMS(2,1), source_RMS(3,1), source_RMS(1,2)/1e9, source_RMS(2,2)/1e9, source_RMS(3,2)/1e9;
                best_RMS(1,1), best_RMS(2,1), best_RMS(3,1), best_RMS(1,2)/1e9, best_RMS(2,2)/1e9, best_RMS(3,2)/1e9];
    
    % 创建格式化的单元格数据
    data_cell = cell(length(band_names), 6);
    for i = 1:length(band_names)
        data_cell{i,1} = format_rms(rms_data(i,1), 'acc');
        data_cell{i,2} = format_rms(rms_data(i,2), 'acc');
        data_cell{i,3} = format_rms(rms_data(i,3), 'acc');
        data_cell{i,4} = format_rms(rms_data(i,4), 'disp');
        data_cell{i,5} = format_rms(rms_data(i,5), 'disp');
        data_cell{i,6} = format_rms(rms_data(i,6), 'disp');
    end
    
    % 创建表格图形
    fig = figure('Name','RMS 对比表','Units','pixels','Color','w');
    t = uitable('Parent', fig, 'Data', data_cell, 'RowName', band_names, ...
        'ColumnName', col_names, 'Units', 'normalized', 'Position', [0 0 1 1], ...
        'FontSize', 12, 'ColumnWidth', {150, 150, 150, 150, 150, 150});
    set(t, 'BackgroundColor', [1 1 1], 'ForegroundColor', [0 0 0]);
    
    % 设置图形大小
    pixel_width = 150*6 + 150;
    pixel_height = 60*length(band_names) + 120;
    set(fig, 'Position', [100, 100, pixel_width, pixel_height]);

    % 命令行输出
    fprintf('\n================ RMS 对比结果 ================\n');
    fprintf('%-25s', '信号名称');
    for j = 1:length(col_names)
        fprintf('%-20s', col_names{j});
    end
    fprintf('\n');
    
    for i = 1:length(band_names)
        fprintf('%-25s', band_names{i});
        for j = 1:6
            fprintf('%-20s', data_cell{i,j});
        end
        fprintf('\n');
    end
    fprintf('==============================================\n');
end

end

%% === 局部函数 ===
function out = format_rms(val, kind)
    % 该函数用于格式化输出 RMS 值，区分加速度和位移单位
    if strcmp(kind, "disp")
        if val >= 1e-6
            out = sprintf('%.2f μm', val * 1e6);  % 大于1μm时以μm显示
        elseif val >= 1e-9
            out = sprintf('%.2f nm', val * 1e9);  % 大于1nm时以nm显示
        else
            out = sprintf('%.2e m', val);         % 小于1nm时以m显示
        end
    elseif strcmp(kind, "acc")
        if val >= 1e-6
            out = sprintf('%.2f μg', val * 1e6);  % 大于1μg时以μg显示
        elseif val >= 1e-9
            out = sprintf('%.2f ng', val * 1e9);  % 大于1ng时以ng显示
        else
            out = sprintf('%.2e g', val);         % 小于1ng时以g显示
        end
    else
        out = 'N/A';  % 如果无法识别类型，返回N/A
    end
end