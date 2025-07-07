% 已知参数
M = 12.6;                % M_tower (kg)
g = 9.81;                % 重力加速度 (m/s^2)

% 材料属性 (黄铜C10100)
G = 50e9;                % 剪切模量 (Pa)
rho = 9000;              % 密度 (kg/m^3)
sigma_yt = 400e6;        % 抗拉屈服强度 (Pa)
zeta = 5e-5;             % 阻尼比 - 低温下可能降低

% 设计固有频率目标
f0_vertical = 0.84;                            % 目标固有频率 (Hz)
k_target = M * (2 * pi * f0_vertical)^2;       % 理想弹簧刚度 (N/m)

% 参数搜索范围
d_wire_range = 1e-3 : 0.1e-3 : 20e-3;   % 线径范围 (m)
d_in_range   = 5e-3 : 0.1e-3 : 0.15;    % 弹簧内径范围 (m) 

% 材料疲劳特性 (基于ASME标准)
tau_yield = 0.58 * sigma_yt;           % 剪切屈服强度 (Pa)
tau_endurance = 0.25 * sigma_yt;       % 剪切疲劳极限 (Pa) - Goodman曲线
FOS_min = 1.5;                         % 最小安全系数

% 初始化
results = [];
best_peak = Inf;
best_H = [];
best_params = [];

% 循环遍历参数组合
for i = 1:length(d_wire_range)
    for j = 1:length(d_in_range)
        d_wire = d_wire_range(i);
        d_in   = d_in_range(j);
        
        % 弹簧几何计算
        d_out = d_in + 2 * d_wire;
        D = (d_in + d_out) / 2;
        
        % 弹簧旋绕比
        c_index = D / d_wire;
        if c_index < 4 || c_index > 16
            continue; 
        end

        % 计算理论圈数
        n_calc = (G * d_wire^4) / (8 * D^3 * k_target);
        n_total_options = unique(round([n_calc+1.5, n_calc+1.8, n_calc+2, n_calc+2.2]));
        
        for n_total = n_total_options
            if n_total < 3
                continue;
            end
            n_eff = n_total - 2;  % 有效圈数
            
            % 实际刚度计算
            k_actual = (G * d_wire^4) / (8 * D^3 * n_eff);
            
            % 弹簧质量计算
            A_coil = pi * (d_wire^2 / 4);
            L_wire = n_total * pi * D; 
            m_s = rho * A_coil * L_wire;
            m_eq = M + (1/3) * m_s;      % 等效质量
            
            % 静载伸长
            delta_static = m_eq * g / k_actual;
            L_eq = n_total * d_wire + delta_static;
            
            % 径向固有频率
            f0_radial = sqrt(g / L_eq) / (2 * pi);

            % 长度约束
            if L_eq < 0.1 || L_eq > 0.75
                continue;
            end
            
            % 剪应力计算 (Wahl修正)
            Kw = (4*c_index - 1)/(4*c_index - 4) + 0.615/c_index;
            F_static = m_eq * g;
            tau_static = Kw * (8 * F_static * D) / (pi * d_wire^3);

            % 循环载荷条件
            tau_min = 0;                % 最小应力
            tau_max = tau_static;        % 最大应力
            tau_mean = (tau_max + tau_min)/2;   % 平均应力
            tau_amp = (tau_max - tau_min)/2;    % 应力幅值
            
            % Goodman疲劳准则
            goodman_ratio = tau_amp/tau_endurance + tau_mean/tau_yield;
            FOS_goodman = 1/goodman_ratio;
            
            % 静态强度安全系数
            FOS_static = tau_yield / tau_static;
            
            % 强度判据
            if tau_static > 0.5 * tau_yield  % 静强度裕度不足
                continue;
            end
            if FOS_goodman < FOS_min        % 疲劳安全系数不足
                continue;
            end
            
            % 阻尼系数
            c = 2 * zeta * sqrt(k_actual * m_eq);
            
           % 存储结果
            results = [results; ...
                d_wire*1000, d_in*1000, d_out*1000, D*1000, ...
                c_index, n_total, n_eff, d_wire*1000, n_total*d_wire*1000, L_eq*1000, ...
                A_coil*1e6, m_s, m_eq, c, k_actual, ...
                sqrt(k_actual/m_eq)/(2*pi), tau_static/1e6, ...
                FOS_static, FOS_goodman, f0_radial];
            
            % 频响分析
            f_plot = linspace(0.01, 100, 1000);    % 频率范围 (Hz)
            omega = 2 * pi * f_plot;               % 角频率范围 (rad/s)
            wn = sqrt(k_actual/m_eq);
            H = 1./sqrt((1 - (omega/wn).^2).^2 + (2*zeta*omega/wn).^2);
            H_peak = max(H);
            if H_peak < best_peak
                best_peak = H_peak;
                best_H = H;
                best_params = [d_wire, D, n_total, n_eff, m_s, m_eq, k_actual, ...
                    sqrt(k_actual/m_eq)/(2*pi), FOS_static, FOS_goodman, f0_radial];
            end
        end
    end
end

% 结果处理与显示
if ~isempty(results)
    % 绘制最佳曲线
    figure;
    semilogy(f_plot, best_H, 'r-', 'LineWidth', 2, 'DisplayName', '最佳组合');
    xlabel('频率 (Hz)');
    ylabel('幅值响应 |H(\omega)|');
    title('频率响应曲线');
    grid on;
    set(gca, 'YScale', 'log');
    ylim([1e-3, 1e2]);
    legend('show');
    
    % 结果表格
    header = {'d_wire_mm', 'd_in_mm', 'd_out_mm', 'D_mm', 'c_index', ...
        'n_total', 'n_eff', 'p_mm', 'L0_mm', 'L_eq_mm', 'A_mm2', 'm_s_kg', ...
        'm_eq_kg', 'c_Ns/m', 'k_N/m', 'f_n_Hz', 'tau_max_MPa', 'FOS_static', 'FOS_fatigue', 'f0_radial_Hz'};
    result_table = array2table(results, 'VariableNames', header);
    
    % 四舍五入显示
    for col = {'d_wire_mm','d_in_mm','d_out_mm','D_mm','p_mm','L0_mm','L_eq_mm','A_mm2'}
        result_table.(col{1}) = round(result_table.(col{1}), 1);
    end
    for col = {'c_index','m_s_kg','m_eq_kg','c_Ns/m','k_N/m','f_n_Hz','tau_max_MPa','FOS_static','FOS_fatigue','f0_radial_Hz'}
        result_table.(col{1}) = round(result_table.(col{1}), 2);
    end
    
    disp('满足设计约束的弹簧参数:');
    disp(result_table);
    
    % 最佳参数输出
    if ~isempty(best_params)
        fprintf('\n=== 最佳弹簧参数 ===\n');
        fprintf('线径: %.1f mm\n', best_params(1)*1000);
        fprintf('中径: %.1f mm\n', best_params(2)*1000);
        fprintf('总圈数: %d (有效圈数: %d)\n', best_params(3), best_params(4));
        fprintf('弹簧质量: %.3f kg\n', best_params(5));
        fprintf('等效质量: %.3f kg\n', best_params(6));
        fprintf('刚度: %.1f N/m\n', best_params(7));
        fprintf('轴向固有频率: %.2f Hz\n', best_params(8));
        fprintf('静强度安全系数: %.2f\n', best_params(9));
        fprintf('疲劳安全系数: %.2f\n', best_params(10));
        fprintf('径向固有频率: %.2f Hz\n', best_params(11));
    end
else
    disp('未找到满足所有约束的解，建议:');
    disp('1. 扩大参数搜索范围');
    disp('2. 考虑更高强度的材料');
    disp('3. 调整目标频率');
end