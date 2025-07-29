% 考虑疲劳极限（经验值），计算已知固有频率下，弹簧的 K 值以及疲劳 & 屈服强度极限载荷  
% 寻找最优的阻尼系数 C，并使用最优参数计算减振效果

% === 基础参数定义 ===
M = 12.6;                % 载荷质量 (kg)
g = 9.81;                % 重力加速度 (m/s^2)

% 材料属性 (黄铜)
G = 77.5e9;                % 剪切模量 (Pa)
rho = 7955;              % 密度 (kg/m^3)
sigma_b = 565e6;         % 抗拉屈服强度 (Pa)

% 固有频率目标
f0_vertical = 1.0;                 
k_target = M * (2 * pi * f0_vertical)^2;

% 搜索范围
d_wire_range = 1e-3:1e-3:5e-3;      % 线径范围 1-5mm
d_in_range = 5e-3:1e-3:9.5e-2;      % 内径范围 5-95mm
d_hook_range = 1e-3:1e-3:5e-3;      % 挂钩直径范围 1-5mm
r_hook_range = 3e-3:1e-3:10e-3;      % 挂钩半径范围 3-10mm

results = [];
best_freq = Inf;         % 初始化最佳频率（低于目标值的最小频率）
best_params = [];        % 存储最佳参数

% 五重循环遍历所有参数组合
for i = 1:length(d_wire_range)
    for j = 1:length(d_in_range)
        for m = 1:length(d_hook_range)
            for n = 1:length(r_hook_range)
                d_wire = d_wire_range(i);
                d_in   = d_in_range(j);
                d_hook = d_hook_range(m);
                r_hook = r_hook_range(n);
                
                % 计算外径和中径
                d_out = d_in + 2 * d_wire;
                D = (d_in + d_out) / 2;
                c_index = D / d_wire;
                
                % 外径约束 (d_out ≤ 100mm)
                if d_out > 0.1
                    continue;
                end
                
                % 计算有效圈数选项
                n_calc = (G * d_wire^4) / (8 * D^3 * k_target);
                n_eff_options = unique(round([n_calc+1.5, n_calc+2, n_calc+2.2]));
                
                % 遍历有效圈数选项
                for k = 1:length(n_eff_options)
                    n_eff = n_eff_options(k);
                    n_total = n_eff + 2;  % 总圈数 = 有效圈数 + 2端部圈
                    
                    % 计算实际刚度
                    k_actual = (G * d_wire^4) / (8 * D^3 * n_eff);
                    
                    % 计算弹簧质量
                    A_coil = pi * (d_wire^2 / 4);         % 线材横截面积
                    L_wire = n_eff * pi * D;              % 弹簧线材长度
                    m_s = rho * A_coil * L_wire;          % 弹簧质量
                    m_eq = M + (1/3) * m_s;               % 等效质量
                    
                    % 计算静态变形和装配长度
                    delta_static = m_eq * g / k_actual;
                    L_eq = n_total * d_wire + delta_static + 2 * d_hook + 2 * r_hook;
                    
                    % 装配长度约束 (L_eq ≤ 330mm)
                    if L_eq > 0.53
                        continue;
                    end
                    
                    % 计算径向固有频率
                    f0_radial = sqrt(g / L_eq) / (2 * pi);
                    
                    % 计算最大载荷和剪应力
                    F_max = m_eq * g;
                    Kw = (4*c_index - 1)/(4*c_index - 4) + 0.615/c_index;  % 曲度系数
                    tau_e = Kw * (8 * F_max * D) / (pi * d_wire^3);  % 最大剪应力
                    
                    % 疲劳安全系数检查
                    FOS_e = sigma_b / tau_e;
                    if FOS_e < 1/0.45  % 安全系数不足
                        continue;
                    end
                    
                    % 计算最大拉应力
                    kappa_3 = (4 * c_index^2 - c_index - 1) / (4 * c_index * (c_index - 1));
                    kappa_3_prime = kappa_3 + 1 / (4 * c_index);
                    sigma_max = kappa_3_prime * (16 * D * F_max) / (pi * d_wire^3);
                    
                    % 最大拉应力检查 (σ_max < 0.7σ_b)
                    if sigma_max >= 0.7 * sigma_b
                        continue;
                    end
                    
                    % 计算实际轴向固有频率
                    actual_freq = sqrt(k_actual/m_eq)/(2*pi);
                    
                    % 保存所有满足约束的结果
                    results = [results;
                        d_wire*1000, d_in*1000, d_out*1000, D*1000, ...
                        c_index, n_total, n_eff, d_wire*1000, ...
                        n_total*d_wire*1000, L_eq*1000, A_coil*1e6, ...
                        m_s, m_eq, k_actual, ...
                        actual_freq, ...
                        tau_e/1e6, FOS_e, f0_radial, sigma_max/1e6];
                    
                    % 更新最佳参数（寻找低于目标频率的最小频率）
                    if actual_freq < f0_vertical && actual_freq < best_freq
                        best_freq = actual_freq;
                        best_params = [d_wire, D, n_total, n_eff, m_s, m_eq, k_actual, ...
                            actual_freq, FOS_e, f0_radial, sigma_max];
                    end
                end  % 结束k循环（有效圈数）
            end  % 结束n循环（挂钩半径）
        end  % 结束m循环（挂钩直径）
    end  % 结束j循环（内径）
end  % 结束i循环（线径）

% 检查是否有满足约束的解
if ~isempty(results)
    % 显示结果表头
    header = {'线径_d_mm', '内径_din_mm', '外径_dout_mm', '中径_D_mm', '旋绕比_c', ...
        '总圈数_n_total', '有效圈数_n_eff', '节距_p_mm', '自由长度_L0_mm', ...
        '装配长度_Leq_mm', '横截面积_A_mm2', '弹簧质量_ms_kg', ...
        '等效质量_meq_kg', '刚度_k_N_m', '轴向固频_fn_Hz', ...
        '最大剪应力_tau_MPa', '疲劳安全系数_FOSf', '径向固频_fr_Hz', ...
        '最大拉应力_sigma_MPa'};
    
    disp('满足设计约束的弹簧参数:');
    fprintf('\n%-10s %-10s %-10s %-10s %-10s %-10s %-10s %-10s %-10s %-10s %-10s %-12s %-12s %-10s %-10s %-12s %-12s %-10s %-10s\n', header{:});
    
    % 显示所有满足约束的结果
    for i = 1:size(results,1)
        fprintf('%-10.2f %-10.2f %-10.2f %-10.2f %-10.2f %-10d %-10d %-10.2f %-10.2f %-10.2f %-10.2f %-12.4f %-12.4f %-10.1f %-10.2f %-12.2f %-12.2f %-10.2f %-10.2f\n', results(i,:));
    end

    % 输出最佳参数
    if ~isempty(best_params)
        fprintf('\n=== 最佳弹簧参数 (最小频率: %.4f Hz) ===\n', f0_vertical, best_freq);
        fprintf('线径: %.1f mm\n', best_params(1)*1000);
        fprintf('中径: %.1f mm\n', best_params(2)*1000);
        fprintf('总圈数: %d (有效圈数: %d)\n', best_params(3), best_params(4));
        fprintf('弹簧质量: %.4f kg\n', best_params(5));
        fprintf('等效质量: %.4f kg\n', best_params(6));
        fprintf('刚度: %.1f N/m\n', best_params(7));
        fprintf('轴向固有频率: %.4f Hz (目标: %.1f Hz)\n', best_params(8), f0_vertical);
        fprintf('疲劳安全系数: %.2f\n', best_params(9));
        fprintf('径向固有频率: %.2f Hz\n', best_params(10));
        fprintf('最大拉应力: %.2f MPa (许用值: %.2f MPa)\n', best_params(11)/1e6, 0.7*sigma_b/1e6);
    else
        fprintf('\n=== 警告：未找到低于目标频率 %.1f Hz的弹簧设计 ===\n', f0_vertical);
        fprintf('=== 将选择最接近目标频率的设计 ===\n');
        
        % 寻找最接近目标频率的设计
        freq_diffs = abs(results(:,15) - f0_vertical);
        [min_diff, min_idx] = min(freq_diffs);
        best_params = [results(min_idx,1)/1000, results(min_idx,4)/1000, results(min_idx,6), ...
            results(min_idx,7), results(min_idx,12), results(min_idx,13), results(min_idx,14), ...
            results(min_idx,15), results(min_idx,17), results(min_idx,18), results(min_idx,19)*1e6];
        
        fprintf('线径: %.1f mm\n', best_params(1)*1000);
        fprintf('中径: %.1f mm\n', best_params(2)*1000);
        fprintf('总圈数: %d (有效圈数: %d)\n', best_params(3), best_params(4));
        fprintf('弹簧质量: %.4f kg\n', best_params(5));
        fprintf('等效质量: %.4f kg\n', best_params(6));
        fprintf('刚度: %.1f N/m\n', best_params(7));
        fprintf('轴向固有频率: %.4f Hz (目标: %.1f Hz)\n', best_params(8), f0_vertical);
        fprintf('疲劳安全系数: %.2f\n', best_params(9));
        fprintf('径向固有频率: %.2f Hz\n', best_params(10));
        fprintf('最大拉应力: %.2f MPa (许用值: %.2f MPa)\n', best_params(11), 0.7*sigma_b/1e6);
    end

    % ============== 阻尼优化部分 ==============
    % 从最佳参数中提取关键值
    k_actual = best_params(7);   % 刚度 (N/m)
    m_eq = best_params(6);       % 等效质量 (kg)
    fn = best_params(8);         % 轴向固有频率 (Hz)
    wn = 2*pi*fn;                % 固有角频率 (rad/s)
    
    % 定义阻尼系数范围 (N·s/m)
    c_range = linspace(0.1, 1000, 10000);  % 扩大阻尼系数搜索范围
    
    % 频率范围 (0-100Hz)
    f_range = 0:0.1:100;         % 0Hz到100Hz，步长0.1Hz
    omega_range = 2*pi*f_range;   % 角频率范围
    
    % 初始化优化变量
    best_c = 0;
    min_T_energy = Inf;          % 初始化最小传递率能量指标
    best_T = [];
    
    % 用于存储积分结果随阻尼系数的变化
    T_energy_values = zeros(size(c_range));
    zeta_values = zeros(size(c_range));
    
    % 常数 C = 2*sqrt(k_actual*m_eq)
    C_constant = 2*sqrt(k_actual*m_eq);
    
    % 遍历阻尼系数
    for idx = 1:length(c_range)
        c = c_range(idx);
        % 计算阻尼比 ζ = c/(2√(k m))
        zeta = c / C_constant;
        zeta_values(idx) = zeta;
        
        % 计算传递率 (基础激励模型)
        T = zeros(size(omega_range));
        for j = 1:length(omega_range)
            omega = omega_range(j);
            r = omega/wn;  % 频率比
            
            % 传递率公式 (ISO 2011标准)
            % T = √[1 + (2ζr)^2] / √[(1-r^2)^2 + (2ζr)^2]
            numerator = sqrt(1 + (2*zeta*r)^2);
            denominator = sqrt((1 - r^2)^2 + (2*zeta*r)^2);
            T(j) = numerator / denominator;
        end
        
        % 计算传递率平方积分 (0-100Hz)
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
    
    % 输出最佳阻尼参数
    fprintf('\n=== 最佳阻尼参数 ===\n');
    fprintf('最佳阻尼系数 c = %.2f N·s/m\n', best_c);
    fprintf('对应阻尼比 ζ = %.4f\n', best_zeta);
    fprintf('最小峰值传递率 = %.4f\n', min_peak_T);
    fprintf('最小平均传递率 = %.4f\n', min_avg_T);
    fprintf('最小传递率积分 (0-100Hz) = %.4f\n', min_T_energy);

    % 绘制传递率曲线
    figure('Name', '传递率曲线', 'Units', 'inches', 'Position', [1, 1, 9.59, 4.22]);
    semilogx(f_range, best_T, 'b-', 'LineWidth', 2);
    hold on;
    % 添加固有频率线
    plot([fn, fn], [0, max(best_T)], 'r--', 'LineWidth', 1.5, 'DisplayName', '固有频率位置');  
    % 添加根号二倍固有频率线
    fn_sqrt2 = fn * sqrt(2);
    plot([fn_sqrt2, fn_sqrt2], [0, max(best_T)], 'g--', 'LineWidth', 1.5, 'DisplayName', '√2倍固有频率位置');
    xlabel('频率 (Hz)');
    ylabel('传递率 |T|');
    title(sprintf('传递率曲线 (c=%.2f N·s/m, ζ=%.4f)', best_c, best_zeta));
    text(0.5, 0.8, sprintf('$T = \\frac{\\sqrt{1 + (2\\zeta r)^2}}{\\sqrt{(1 - r^2)^2 + (2\\zeta r)^2}}$', ...
        best_zeta), 'Interpreter', 'latex', 'FontSize', 14, 'Units', 'normalized');
    legend('传递率曲线', '固有频率位置', '√2倍固有频率位置', 'Location', 'best');
    grid on;
    xlim([0.1, 100]); % 从0.1Hz开始显示，避免0Hz问题
    ylim([0, max(best_T) * 1.1]);
    
    % ===== 图2：传递率积分随阻尼系数的变化曲线 =====
    figure('Name', '传递率积分随阻尼系数变化', 'Units', 'inches', 'Position', [1, 1, 9.59, 4.22]);
    semilogx(c_range, T_energy_values, 'b-', 'LineWidth', 2);
    hold on;
    plot([best_c, best_c], [min(T_energy_values), max(T_energy_values)], 'r--', 'LineWidth', 1.5);
    xlabel('阻尼系数 c (N·s/m)');
    ylabel('传递率积分 E (0-100Hz)');
    title('传递率积分随阻尼系数变化');
    
    % 添加积分公式标注和最佳参数（使用LaTeX渲染）
    text(0.05, 0.85, sprintf('$E = \\int_{0\\mathrm{Hz}}^{100\\mathrm{Hz}} T^2(f)  df$'), ...
        'Interpreter', 'latex', 'FontSize', 14, 'Units', 'normalized');
    text(0.05, 0.75, sprintf('$c_{best} = %.2f$ N$\\cdot$s/m', best_c), ...
        'Interpreter', 'latex', 'FontSize', 14, 'Units', 'normalized');
    text(0.05, 0.65, sprintf('$\\zeta_{best} = %.4f$', best_zeta), ...
        'Interpreter', 'latex', 'FontSize', 14, 'Units', 'normalized');
    
    legend('传递率积分', '最佳阻尼系数', 'Location', 'best');
    grid on;
    
    % ===== 图3：传递率积分随阻尼比的变化曲线 =====
    figure('Name', '传递率积分随阻尼比变化', 'Units', 'inches', 'Position', [1, 1, 9.59, 4.22]);
    plot(zeta_values, T_energy_values, 'b-', 'LineWidth', 2);
    hold on;
    plot([best_zeta, best_zeta], [min(T_energy_values), max(T_energy_values)], 'r--', 'LineWidth', 1.5);
    xlabel('阻尼比 ζ');
    ylabel('传递率积分 E (0-100Hz)');
    title('传递率积分随阻尼比变化');
    
    % 添加积分公式标注和最佳参数（使用LaTeX渲染）
    text(0.05, 0.85, sprintf('$E = \\int_{0\\mathrm{Hz}}^{100\\mathrm{Hz}} T^2(f)  df$'), ...
        'Interpreter', 'latex', 'FontSize', 14, 'Units', 'normalized');
    text(0.05, 0.75, sprintf('$\\zeta_{best} = %.4f$', best_zeta), ...
        'Interpreter', 'latex', 'FontSize', 14, 'Units', 'normalized');
    
    legend('传递率积分', '最佳阻尼比', 'Location', 'best');
    grid on;

    % ============== 减振效果分析 ==============
    % 选择 CSV 文件读取加速度数据
    [fileName, filePath] = uigetfile('*.csv', '选择振源加速度 CSV 文件');
    if isequal(fileName, 0)
        error('用户取消了文件选择。');
    end
    fullFileName = fullfile(filePath, fileName);
    
    % 读取 CSV 文件（保留前4行标题）
    fid = fopen(fullFileName, 'r');
    headerLines = cell(4,1);
    for i = 1:4
        headerLines{i} = fgetl(fid);
    end
    fclose(fid);
    
    % 读取数据部分
    opts = detectImportOptions(fullFileName, 'NumHeaderLines', 4);
    data = readmatrix(fullFileName, opts);
    time = data(:, 1);
    voltage = data(:, 2);  % 电压信号
    
    % 传感器参数
    gain = 100;         % 增益
    sensitivity = 1.026; % 灵敏度 (g/V)
    
    % 转换为加速度 (g) - 减振前的原始数据
    acc_base_g = voltage / ( gain * sensitivity );
    
    % 转换为 SI 单位的加速度并去直流分量
    acc_base = acc_base_g * g;               % 将基础加速度转换为 m/s^2
    acc_base = acc_base - mean(acc_base);    % 去除直流分量
    
    % 采样参数
    dt = mean(diff(time));
    fs = 1 / dt;
    N = length(time);
    
    % 计算频域传递函数 H(jω)
    omega = 2 * pi * fs * (0:(N/2)) / N;
    H = zeros(size(omega));
    for ii = 1:length(omega)
        s = 1i * omega(ii);
        H(ii) = (best_c * s + k_actual) / (m_eq * s^2 + best_c * s + k_actual);
    end
    % 将传递函数扩展为完整频谱（共轭对称）
    H_full = [H, conj(flip(H(2:end-1)))];
    
    % 频域滤波计算隔振后的加速度
    fft_base = fft(acc_base);
    fft_isolated = fft_base .* H_full.';
    acc_isolated = real(ifft(fft_isolated));
    
    % 去直流分量
    acc_isolated = acc_isolated - mean(acc_isolated);
    
    % ============== 绘制减振前后对比图 ==============
    % 图4：时域加速度对比
    fig_time = figure('Name', '减振前后加速度时域对比', 'Units', 'inches', 'Position', [1, 1, 9.59, 4.22]);
    
    % 使用去直流分量后的减振前数据（转换为g单位）
    acc_base_g_detrend = acc_base / g;
    
    plot(time, acc_base_g_detrend, 'b-', 'LineWidth', 1.5, 'DisplayName', '减振前 (原始数据, 去直流)'); 
    hold on;
    plot(time, acc_isolated / g, 'r-', 'LineWidth', 1.5, 'DisplayName', '减振后 (仿真结果)'); 
    xlabel('时间 (s)');
    ylabel('加速度 (g)');
    title('减振前后加速度时域对比');
    legend('show', 'Location', 'best');
    grid on;
    % 设置横轴范围与数据长度一致
    xlim([min(time), max(time)]);
    
    % ============== 输出减振后的CSV文件 ==============
    % 将减振后加速度转换为电压信号
    acc_isolated_g = acc_isolated / g; % 转换为g单位
    voltage_isolated = acc_isolated_g * sensitivity * gain;
    
    % 创建输出文件名
    [~, name, ext] = fileparts(fileName);
    outputFileName = fullfile(filePath, [name '_isolated' ext]);
    
    % 写入CSV文件（包含原始标题）
    fid = fopen(outputFileName, 'w');
    for i = 1:4
        fprintf(fid, '%s\n', headerLines{i});
    end
    for i = 1:length(time)
        fprintf(fid, '%.6f,%.6f\n', time(i), voltage_isolated(i));
    end
    fclose(fid);
    
    fprintf('减振后的加速度数据已保存为: %s\n', outputFileName);
    
    % ============== PSD 和 LPSD 分析 ==============
    % 计算频域参数 - 使用1000000点FFT
    nfft = 500000;  % 100万点FFT
    window = hanning(nfft);
    overlap = round(0.5 * nfft);
    
    % 计算减振前后的功率谱密度 (PSD)
    [pxx_base, f] = pwelch(acc_base, window, overlap, nfft, fs);
    [pxx_isolated, ~] = pwelch(acc_isolated, window, overlap, nfft, fs);
    
    % 计算加速度 LPSD
    lpsd_base = sqrt(pxx_base) / g;         % 加速度 LPSD [g/√Hz]
    lpsd_isolated = sqrt(pxx_isolated) / g; % 加速度 LPSD [g/√Hz]
    
    % 计算位移 LPSD (通过加速度转换)
    lpsd_base_disp = g ./ ((2*pi*f).^2) .* lpsd_base;           % 位移 LPSD [m/√Hz]
    lpsd_isolated_disp = g ./ ((2*pi*f).^2) .* lpsd_isolated;   % 位移 LPSD [m/√Hz]
    
    % 创建 PSD 对比图
    fig_psd = figure('Name', '减振前后 PSD 对比', 'Units', 'inches', 'Position', [1, 1, 9.59, 4.22]);
    loglog(f, pxx_base / g^2, 'b-', 'LineWidth', 1.5, 'DisplayName', '减振前');
    hold on;
    loglog(f, pxx_isolated / g^2, 'r-', 'LineWidth', 1.5, 'DisplayName', '减振后');
    xlabel('频率 (Hz)');
    ylabel('PSD [g²/Hz]');
    title('减振前后功率谱密度对比');
    legend('show', 'Location', 'best');
    grid on;
    xlim([0.1, 200]);
    
    % 创建加速度 LPSD 对比图
    fig_acc_lpsd = figure('Name', '减振前后加速度 LPSD', 'Units', 'inches', 'Position', [1, 1, 9.59, 4.22]);
    loglog(f, lpsd_base, 'b-', 'LineWidth', 1.5, 'DisplayName', '减振前');
    hold on;
    loglog(f, lpsd_isolated, 'r-', 'LineWidth', 1.5, 'DisplayName', '减振后');
    xlabel('频率 (Hz)');
    ylabel('LPSD [g/√Hz]');
    title('减振前后加速度线性谱密度对比');
    legend('show', 'Location', 'best');
    grid on;
    xlim([0.1, 200]);
    
    % 创建位移 LPSD 对比图
    fig_disp_lpsd = figure('Name', '减振前后位移 LPSD', 'Units', 'inches', 'Position', [1, 1, 9.59, 4.22]);
    loglog(f, lpsd_base_disp * 1e9, 'b-', 'LineWidth', 1.5, 'DisplayName', '减振前');     % 转换为 nm/√Hz
    hold on;
    loglog(f, lpsd_isolated_disp * 1e9, 'r-', 'LineWidth', 1.5, 'DisplayName', '减振后'); % 转换为 nm/√Hz
    xlabel('频率 (Hz)');
    ylabel('LPSD [nm/√Hz]');
    title('减振前后位移线性谱密度对比');
    legend('show', 'Location', 'best');
    grid on;
    xlim([0.1, 200]);
    
    % ============== RMS 计算 ==============
    % 定义频带范围
    band_edges = [0.1, 40; 0.1, 100; 1, 40; 40, 100; 1, 100];
    band_names = {'[0-40] Hz', '[0-100] Hz', '[1-40] Hz', '[40-100] Hz', '[1-100] Hz'};
    df = mean(diff(f));  % 频率分辨率
    
    % 计算各频段的 RMS 加速度（单位：μg）和 RMS 位移（单位：nm）
    nBands = length(band_names);  % 自动获取频段个数
    RMS_base_acc = zeros(1, nBands);
    RMS_isolated_acc = zeros(1, nBands);
    RMS_base_disp = zeros(1, nBands);
    RMS_isolated_disp = zeros(1, nBands);

for iBand = 1:nBands
    idx = (f >= band_edges(iBand, 1) & f <= band_edges(iBand, 2));
    
    % 加速度 RMS (μg)
    RMS_base_acc(iBand) = sqrt(sum((lpsd_base(idx) .^ 2) * df)) * 1e6;
    RMS_isolated_acc(iBand) = sqrt(sum((lpsd_isolated(idx) .^ 2) * df)) * 1e6;
    
    % 位移 RMS (nm)
    RMS_base_disp(iBand) = sqrt(sum((lpsd_base_disp(idx) .^ 2) * df)) * 1e9;
    RMS_isolated_disp(iBand) = sqrt(sum((lpsd_isolated_disp(idx) .^ 2) * df)) * 1e9;
end
    
    % 计算减振效果百分比
    reduction_acc = (RMS_base_acc - RMS_isolated_acc) ./ RMS_base_acc * 100;
    reduction_disp = (RMS_base_disp - RMS_isolated_disp) ./ RMS_base_disp * 100;
    
    % ============== 创建 RMS 结果表格 ==============
    % 创建表格数据（3行7列）
   rms_results = cell(nBands, 7);
for iBand = 1:nBands
    rms_results{iBand,1} = band_names{iBand};
    rms_results{iBand,2} = sprintf('%.2f', RMS_base_acc(iBand));
    rms_results{iBand,3} = sprintf('%.2f', RMS_isolated_acc(iBand));
    rms_results{iBand,4} = sprintf('%.1f%%', reduction_acc(iBand));
    rms_results{iBand,5} = sprintf('%.2f', RMS_base_disp(iBand));
    rms_results{iBand,6} = sprintf('%.2f', RMS_isolated_disp(iBand));
    rms_results{iBand,7} = sprintf('%.1f%%', reduction_disp(iBand));
end
    
    % 表头定义
    col_names = {'频带', '减振前加速度 (μg)', '减振后加速度 (μg)', '减振效果 (%)', ...
                 '减振前位移 (nm)', '减振后位移 (nm)', '减振效果 (%)'};
    
    % 显示 RMS 结果表格
    fig_rms = figure('Name', 'RMS 对比结果', 'Units', 'inches', 'Position', [1, 1, 12, 4]);
    uitable(fig_rms, 'Data', rms_results, ...
                   'ColumnName', col_names, ...
                   'Units', 'normalized', 'Position', [0.05, 0.05, 0.9, 0.9], ...
                   'FontSize', 10, 'RowName', []);
    
    % ============== 命令行输出 RMS 结果 ==============
    fprintf('\n=== 减振效果分析 ===\n');
    fprintf('%-15s %-20s %-20s %-15s %-20s %-20s %-15s\n', '频带', ...
            '减振前加速度(μg)', '减振后加速度(μg)', '减振效果(%)', ...
            '减振前位移(nm)', '减振后位移(nm)', '减振效果(%)');
    fprintf('-------------------------------------------------------------------------------------------\n');
  for iBand = 1:nBands
    fprintf('%-15s %-20.2f %-20.2f %-15.1f %-20.2f %-20.2f %-15.1f\n', ...
            band_names{iBand}, ...
            RMS_base_acc(iBand), RMS_isolated_acc(iBand), reduction_acc(iBand), ...
            RMS_base_disp(iBand), RMS_isolated_disp(iBand), reduction_disp(iBand));
end
else
    disp('未找到满足所有约束的解。');
end