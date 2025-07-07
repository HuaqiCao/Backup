function spring_properties_calculator_auto()
    % 弹窗输入参数
    prompt = {'铜线直径 d (mm):', ...
              '弹簧外径 D_o (mm):', ...
              '弹簧内径 D_i (mm):', ...
              '圈数 N:', ...
              '材料剪切模量 G (GPa):', ...
              '材料阻尼比 zeta (经验值，建议0.02):'};
    dlgtitle = '输入弹簧参数';
    dims = [1 35];
    definput = {'1.5', '16.5', '13.5', '100', '44', '0.02'};
    answer = inputdlg(prompt, dlgtitle, dims, definput);
    if isempty(answer)
        disp('用户取消输入。');
        return;
    end
    
    % 解析输入
    d = str2double(answer{1}) / 1000;         % m
    D_o = str2double(answer{2}) / 1000;       % m
    D_i = str2double(answer{3}) / 1000;       % m
    N = str2double(answer{4});
    G = str2double(answer{5}) * 1e9;           % Pa
    zeta = str2double(answer{6});
    
    % 估算磷铜抗拉强度 sigma_u (Pa)，简单用常数450 MPa
    sigma_u = 450e6;
    
    % 根据经验估算疲劳极限应力和最大工作应力
    sigma_f = 0.5 * sigma_u;       % 疲劳极限取抗拉强度的50%
    sigma_max = 0.75 * sigma_u;    % 最大工作应力取抗拉强度的75%
    
    % 计算中径
    D = (D_o + D_i)/2;
    
    % 计算线材长度和质量
    rho = 8960; % 铜密度，kg/m³
    L = N * pi * D;               % 线材长度，m
    A = pi * (d/2)^2;             % 截面积，m²
    V = L * A;                    % 体积，m³
    m = rho * V;                  % 质量，kg
    
    % 弹簧刚度 k (N/m)
    k = G * d^4 / (8 * D^3 * N);
    
    % 计算阻尼系数 c
    c = 2 * zeta * sqrt(k * m);
    
    % 估算最大载荷 F_max
    F_max = sigma_max * pi * d^3 / (8 * D);
    
    % 疲劳极限载荷 F_fatigue
    F_fatigue = sigma_f * pi * d^3 / (8 * D);
    
    % 显示结果
    msg = sprintf(['计算结果：\n', ...
                   '弹簧质量 m = %.4f kg\n', ...
                   '刚度系数 k = %.2f N/m\n', ...
                   '阻尼系数 c = %.4f Ns/m\n', ...
                   '估算疲劳极限应力 sigma_f = %.1f MPa\n', ...
                   '估算最大工作应力 sigma_max = %.1f MPa\n', ...
                   '最大载荷 F_max = %.2f N\n', ...
                   '疲劳极限载荷 F_fatigue = %.2f N\n'], ...
                   m, k, c, sigma_f/1e6, sigma_max/1e6, F_max, F_fatigue);
               
    msgbox(msg, '弹簧参数计算结果');
end