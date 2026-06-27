from flask import Flask, render_template, request, jsonify
import re

app = Flask(__name__)

REGISTERS = {f"$t{i}": 0 for i in range(10)}
REGISTERS.update({f"$s{i}": 0 for i in range(8)})
REGISTERS.update({"$zero": 0, "$v0": 0, "$v1": 0, "$a0": 0, "$a1": 0, "$a2": 0, "$a3": 0})

def parse_instructions(code):
    instructions = []
    for line in code.strip().split('\n'):
        line = line.split('#')[0].strip()
        if line:
            instructions.append(line)
    return instructions

def get_instruction_info(instr):
    instr = instr.strip()
    parts = re.split(r'[\s,]+', instr)
    op = parts[0].lower() if parts else ''
    
    r_type = ['add', 'sub', 'and', 'or', 'slt', 'nor', 'xor', 'sll', 'srl']
    i_type = ['addi', 'lw', 'sw', 'beq', 'bne', 'slti', 'andi', 'ori']
    j_type = ['j', 'jal', 'jr']
    
    if op in r_type:
        itype = 'R'
        dest = parts[1] if len(parts) > 1 else None
        src1 = parts[2] if len(parts) > 2 else None
        src2 = parts[3] if len(parts) > 3 else None
        return {'op': op, 'type': itype, 'dest': dest, 'src1': src1, 'src2': src2, 'raw': instr}
    elif op in i_type:
        itype = 'I'
        if op in ['lw', 'sw']:
            dest = parts[1] if len(parts) > 1 else None
            # parse offset($reg)
            rest = parts[2] if len(parts) > 2 else ''
            m = re.match(r'(-?\d+)\((\$\w+)\)', rest)
            if m:
                src1 = m.group(2)
                src2 = None
            else:
                src1 = None
                src2 = None
        else:
            dest = parts[1] if len(parts) > 1 else None
            src1 = parts[2] if len(parts) > 2 else None
            src2 = None
        return {'op': op, 'type': itype, 'dest': dest, 'src1': src1, 'src2': src2, 'raw': instr}
    elif op in j_type:
        return {'op': op, 'type': 'J', 'dest': None, 'src1': None, 'src2': None, 'raw': instr}
    else:
        return {'op': op, 'type': '?', 'dest': None, 'src1': None, 'src2': None, 'raw': instr}

def detect_hazards(instructions):
    parsed = [get_instruction_info(i) for i in instructions]
    hazards = []
    stalls = [0] * len(parsed)
    
    for i in range(1, len(parsed)):
        curr = parsed[i]
        
        for j in range(max(0, i-3), i):
            prev = parsed[j]
            distance = i - j
            
            # Data Hazard kontrolü
            if prev['dest'] and prev['dest'] != '$zero':
                sources = [s for s in [curr['src1'], curr['src2']] if s]
                if prev['dest'] in sources:
                    if prev['op'] == 'lw' and distance == 1:
                        hazards.append({
                            'type': 'load-use',
                            'instruction': i,
                            'caused_by': j,
                            'register': prev['dest'],
                            'severity': 'critical',
                            'description': f"Load-Use Hazard: '{parsed[i]['raw']}' komutunun '{prev['dest']}' kaydedicisine ihtiyacı var ancak LW henüz tamamlanmadı. 1 stall gerekli.",
                            'solution': 'Stall (1 cycle) veya kod yeniden düzenleme'
                        })
                        stalls[i] = max(stalls[i], 1)
                    elif distance <= 2 and prev['op'] != 'lw':
                        hazards.append({
                            'type': 'data',
                            'instruction': i,
                            'caused_by': j,
                            'register': prev['dest'],
                            'severity': 'warning',
                            'description': f"Data Hazard (RAW): '{parsed[i]['raw']}' komutunun '{prev['dest']}' kaydedicisine ihtiyacı var. Forwarding ile çözülebilir.",
                            'solution': 'Forwarding (veri yönlendirme)'
                        })
            
            # Control Hazard
            if prev['op'] in ['beq', 'bne', 'j', 'jal', 'jr']:
                if distance <= 2:
                    hazards.append({
                        'type': 'control',
                        'instruction': i,
                        'caused_by': j,
                        'register': None,
                        'severity': 'warning',
                        'description': f"Control Hazard: '{prev['raw']}' dallanma komutu. Pipeline'a yanlış komutlar girebilir.",
                        'solution': 'Branch prediction veya delay slot'
                    })
    
    return parsed, hazards, stalls

def simulate_pipeline(instructions):
    parsed, hazards, stalls = detect_hazards(instructions)
    n = len(parsed)
    stages = ['IF', 'ID', 'EX', 'MEM', 'WB']
    
    # Her instruction için hangi cycle'da hangi stage'de olduğunu hesapla
    pipeline_table = []
    current_cycle = 1
    
    for i, instr in enumerate(parsed):
        extra_stalls = stalls[i]
        start_cycle = current_cycle
        row = {
            'instruction': instr['raw'],
            'type': instr['type'],
            'stages': {},
            'start_cycle': start_cycle,
            'stalls': extra_stalls
        }
        for s_idx, stage in enumerate(stages):
            row['stages'][start_cycle + s_idx + extra_stalls] = stage
        
        pipeline_table.append(row)
        current_cycle += 1 + extra_stalls
    
    total_cycles = current_cycle + 4
    
    return {
        'pipeline_table': pipeline_table,
        'hazards': hazards,
        'total_cycles': total_cycles,
        'total_instructions': n,
        'cpi': round(total_cycles / n, 2) if n > 0 else 0,
        'stall_cycles': sum(stalls)
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/simulate', methods=['POST'])
def simulate():
    data = request.json
    code = data.get('code', '')
    instructions = parse_instructions(code)
    
    if not instructions:
        return jsonify({'error': 'Lütfen en az bir MIPS komutu girin.'})
    
    if len(instructions) > 20:
        return jsonify({'error': 'Maksimum 20 komut desteklenmektedir.'})
    
    result = simulate_pipeline(instructions)
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)
