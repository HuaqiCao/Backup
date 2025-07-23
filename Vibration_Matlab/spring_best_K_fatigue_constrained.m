% 考虑疲劳极限（经验值），计算已知固有频率下，弹簧的K值以及疲劳&屈服强度极限载荷

% 已知参数
M = 12.6;                % 载荷质量 (kg)
g = 9.81;                % 重力加速度 (m/s^2)

% 材料属性 (黄铜)
G = 77e9;                % 剪切模量 (Pa)
rho = 7930;              % 密度 (kg/m^3)
sigma_b = 505e6;         % 抗拉屈服强度 (Pa)

% 固有频率目标
f0_vertical = 1.3;                 
k_target = M * (2 * pi * f0_vertical)^2;

% 搜索范围
d_wire_range = 1e-3:1e-3:5e-3;
d_in_range = 5e-3:1e-3:9.5e-2;
d_hook_range = 1e-3:1e-3:5e-3;
r_hook_range = 2e-3:1e-3:8e-3;

results = [];

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

                    if L_eq > 0.33
                        continue;
                    end

                    % 计算径向固有频率
                    f0_radial = sqrt(g / L_eq) / (2 * pi);
                    
                    F_max = m_eq * g;
                    
                    % 计算最大剪应力和疲劳安全系数
                    Kw = (4*c_index - 1)/(4*c_index - 4) + 0.615/c_index;
                    tau_e = Kw * (8 * F_max * D) / (pi * d_wire^3);
                    FOS_e = sigma_b / tau_e;
                    
                    if FOS_e < 1/0.45
                        continue;
                    end

                    % 计算最大拉应力
                    kappa_3 = (4 * c_index^2 - c_index - 1) / (4 * c_index * (c_index - 1));
                    kappa_3_prime = kappa_3 + 1 / (4 * c_index);
                    sigma_max = kappa_3_prime * (16 * D * F_max) / (pi * d_wire^3);
                    
                    if sigma_max >= 0.7 * sigma_b
                        continue;
                    end

                    % 计算节距
                    p = (L_eq - delta_static - 2*d_hook - 2*r_hook)/n_eff;
                    
                    % 存储所有结果（包含疲劳安全系数、径向频率和最大拉应力）
                    results = [results;
                        d_wire*1000, d_in*1000, d_out*1000, D*1000, ...
                        c_index, n_total, n_eff, ...
                        p*1000, ...  % 节距(mm)
                        n_total*d_wire*1000, ...  % 自由长度(mm)
                        L_eq*1000, ...  % 装配长度(mm)
                        A_coil*1e6, ...  % 横截面积(mm²)
                        m_s, m_eq, k_actual, ...
                        sqrt(k_actual/m_eq)/(2*pi), ...  % 轴向固有频率(Hz)
                        tau_e/1e6, ...  % 最大剪应力(MPa)
                        FOS_e, ...  % 疲劳安全系数
                        f0_radial, ...  % 径向固有频率(Hz)
                        sigma_max/1e6];  % 最大拉应力(MPa)
                end
            end
        end
    end
end

if ~isempty(results)
    % === 1. 选取轴向固有频率最低的作为最佳解 ===
    [~, idx_best] = min(results(:,15));  % 第15列是轴向固频 fn_Hz
    best_params = results(idx_best, :);

    % === 2. 打印表格 ===
    header = {'线径_d_mm', '内径_din_mm', '外径_dout_mm', '中径_D_mm', '旋绕比_c', ...
        '总圈数_n_total', '有效圈数_n_eff', '节距_p_mm', '自由长度_L0_mm', ...
        '装配长度_Leq_mm', '横截面积_A_mm2', '弹簧质量_ms_kg', ...
        '等效质量_meq_kg', '刚度_k_N_m', '轴向固频_fn_Hz', ...
        '最大剪应力_tau_MPa', '疲劳安全系数_FOSf', '径向固频_fr_Hz', ...
        '最大拉应力_sigma_MPa'};
    
    disp('满足设计约束的弹簧参数:');
    fprintf('\n%-10s %-10s %-10s %-10s %-10s %-10s %-10s %-10s %-10s %-10s %-10s %-10s %-10s %-10s %-10s %-10s %-10s %-10s %-10s\n', header{:});

    % 修正打印格式 - 确保所有值正确显示
    for i = 1:size(results,1)
        fprintf('%-10.2f %-10.2f %-10.2f %-10.2f %-10.2f %-10.0f %-10.0f %-10.2f %-10.2f %-10.2f %-10.2f %-10.4f %-10.4f %-10.1f %-10.2f %-10.2f %-10.2f %-10.2f %-10.1f\n', ...
            results(i,1), results(i,2), results(i,3), results(i,4), results(i,5), ...
            results(i,6), results(i,7), results(i,8), results(i,9), results(i,10), ...
            results(i,11), results(i,12), results(i,13), results(i,14), results(i,15), ...
            results(i,16), results(i,17), results(i,18), results(i,19));
    end

    % === 3. 打印最优解 ===
    fprintf('\n=== 最佳弹簧参数（轴向固频最低） ===\n');
    fprintf('线径: %.1f mm\n', best_params(1));
    fprintf('内径: %.1f mm\n', best_params(2));
    fprintf('外径: %.1f mm\n', best_params(3));
    fprintf('中径: %.1f mm\n', best_params(4));
    fprintf('旋绕比: %.2f\n', best_params(5));
    fprintf('总圈数: %d\n', round(best_params(6)));
    fprintf('有效圈数: %d\n', round(best_params(7)));
    fprintf('节距: %.2f mm\n', best_params(8));
    fprintf('自由长度: %.2f mm\n', best_params(9));
    fprintf('装配长度: %.2f mm\n', best_params(10));
    fprintf('横截面积: %.2f mm²\n', best_params(11));
    fprintf('弹簧质量: %.4f kg\n', best_params(12));
    fprintf('等效质量: %.4f kg\n', best_params(13));
    fprintf('刚度: %.1f N/m\n', best_params(14));
    fprintf('轴向固有频率: %.2f Hz\n', best_params(15));
    fprintf('最大剪应力: %.2f MPa\n', best_params(16));
    fprintf('疲劳安全系数: %.2f\n', best_params(17));  % 疲劳安全系数
    fprintf('径向固有频率: %.2f Hz\n', best_params(18));  % 径向固有频率
    fprintf('最大拉应力: %.1f MPa\n', best_params(19));  % 最大拉应力

else
    disp('未找到满足所有约束的解。');
end