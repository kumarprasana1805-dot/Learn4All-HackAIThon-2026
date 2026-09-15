from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import subprocess, shutil

root=Path('/mnt/data/work')
out=root/'static'/'videos'; out.mkdir(parents=True,exist_ok=True)
font_b='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
font_r='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
FB=ImageFont.truetype(font_b,52); FT=ImageFont.truetype(font_r,31); FS=ImageFont.truetype(font_r,25); FM=ImageFont.truetype(font_b,24)
# Six substantial chapters per topic. Each is a 10-second slide.
content={
'fractions':[
('What a fraction means',['Numerator = selected equal parts','Denominator = equal parts in one whole','Denominator cannot be zero','Example: 3/5 means 3 of 5 equal parts']),
('Equivalent & simplest form',['Multiply or divide both parts by the same non-zero number','2/3 = 4/6 = 6/9','Simplest form has no common factor > 1','Use the greatest common factor to simplify']),
('Compare fractions',['Same denominator: compare numerators','Different denominators: use a common denominator','Cross multiplication is another comparison method','Estimate the size before deciding']),
('Add & subtract',['Find a common denominator for unlike fractions','Add/subtract only the numerators after conversion','Keep the denominator common','Simplify the final answer']),
('Multiply & divide',['Multiply numerator by numerator and denominator by denominator','Cancel common factors before multiplying when useful','Division means multiply by the reciprocal of the divisor','Check whether the result size is sensible']),
('Revision example',['1/4 + 2/3 = 3/12 + 8/12','So the answer is 11/12','Never add denominators directly','Revise: simplify, compare, add, subtract, multiply, divide'])],
'geometry':[
('Angle foundations',['Right angle = 90 degrees','Straight angle = 180 degrees','Full turn = 360 degrees','Complementary = 90; supplementary = 180']),
('Triangles',['Interior angles total 180 degrees','Isosceles: two equal sides and opposite angles','Equilateral: three equal sides, each angle 60 degrees','Missing angle = 180 minus the other two']),
('Quadrilaterals',['Interior angles total 360 degrees','Rectangle area = length x breadth','Rectangle perimeter = 2(length + breadth)','Square area = side squared']),
('Circles',['Diameter = 2r','Circumference = 2 pi r','Area = pi r squared','Use the value of pi specified in the question']),
('Coordinate geometry',['Point is written as (x, y)','x controls horizontal position; y controls vertical position','Distance uses horizontal and vertical differences','Midpoint is the average of endpoint coordinates']),
('Worked example',['Triangle angles: 55 degrees, 65 degrees and x','55 + 65 + x = 180','Therefore x = 60 degrees','Exam method: sketch -> rule -> calculation -> unit/check'])],
'algebra':[
('Variables & terms',['Variable = unknown or changing quantity','Constant = fixed value','Coefficient = numerical factor of a variable','In 5x + 3: 5 is coefficient, x variable, 3 constant']),
('Like terms',['Like terms have the same variable part and powers','4x + 3x = 7x','4x + 3y cannot be combined','Combine coefficients, not unlike terms']),
('Equations',['Keep both sides balanced','Use inverse operations to isolate the variable','Do the same operation on both sides','Substitute the answer back to verify']),
('Expansion',['Use the distributive property','2(x + 4) = 2x + 8','Multiply every term inside the bracket','Watch negative signs carefully']),
('Identities & factorisation',['(a+b)^2 = a^2 + 2ab + b^2','(a-b)^2 = a^2 - 2ab + b^2','Factorisation reverses expansion','Look for a common factor first']),
('Worked example',['3x + 5 = 20','Subtract 5: 3x = 15','Divide by 3: x = 5','Check: 3(5) + 5 = 20'])],
'photosynthesis':[
('Definition & equation',['Plants use light energy to make food','Carbon dioxide + water -> glucose + oxygen','Chlorophyll captures light energy','The process mainly occurs in green tissues']),
('Chloroplast & chlorophyll',['Chloroplasts contain the photosynthetic machinery','Chlorophyll is the green light-absorbing pigment','Light energy is converted into chemical energy','Green light is less strongly absorbed than some other wavelengths']),
('Raw materials',['Carbon dioxide enters mainly through stomata','Roots absorb water from soil','Xylem transports water to leaves','Both inputs are needed for the overall process']),
('Products & uses',['Glucose is an important carbohydrate product','Glucose can enter cellular respiration','It can be converted to starch for storage','Oxygen is released during photosynthesis']),
('Limiting factors',['Light intensity can limit the rate','Carbon dioxide concentration can limit the rate','Temperature affects enzyme-controlled reactions','Once one factor stops limiting, another may become limiting']),
('Exam revision',['Remember inputs, conditions and products','Know chloroplast, chlorophyll, stomata and xylem roles','Separate photosynthesis from respiration','Use factor -> effect -> limiting factor in graph questions'])],
'grammar':[
('Sentence structure',['A sentence expresses a complete thought','Subject = who or what the sentence is about','Predicate contains what is said about the subject','Check the complete sentence before correcting it']),
('Parts of speech',['Noun names a person, place, thing or idea','Verb shows an action or state','Adjective modifies a noun','Adverb commonly modifies a verb, adjective or adverb']),
('Agreement',['Singular subjects generally take singular present forms','Plural subjects generally take plural forms','Find the true subject before choosing the verb','Ignore distracting words between subject and verb']),
('Tenses',['Present: I study','Past: I studied','Future: I will study','Use time clues and keep tense consistent unless meaning requires a change']),
('Voice & speech',['Active: subject performs the action','Passive: subject receives the action','Direct speech gives the quoted words','Reported speech changes the structure while preserving meaning']),
('Editing revision',['Check subject-verb agreement','Check tense and pronoun reference','Check articles, prepositions and punctuation','Read for meaning after correcting grammar'])],
'electricity':[
('Current & charge',['Current is rate of flow of charge','I = Q/t','Current unit = ampere','Conventional current direction is defined separately from electron motion']),
('Potential difference',['V = W/Q','It is energy transferred per unit charge','Voltage is measured in volts','Always identify the two points across which voltage is measured']),
('Resistance & Ohm law',['Resistance opposes current','V = IR for an ohmic conductor under suitable conditions','I = V/R and R = V/I','Resistance unit = ohm']),
('Series circuits',['Same current flows through series components','R total = R1 + R2 + ...','Potential differences add across components','Adding series resistance increases total resistance']),
('Parallel circuits',['Same potential difference across each branch','Current divides between branches','Equivalent resistance is below the smallest positive branch resistance','Household appliances use parallel connections for independence']),
('Power & instruments',['P = VI = I squared R = V squared/R','Ammeter -> series','Voltmeter -> parallel','Check units before substitution'])],
'thermodynamics':[
('System & surroundings',['System = part being studied','Surroundings = everything outside','Boundary separates the two','Energy may cross as heat or work']),
('Heat & temperature',['Heat is energy transferred due to temperature difference','Temperature describes thermal state','Internal energy is microscopic energy of the system','Heat is not a substance stored in an object']),
('First law',['Using W as work done by system: Q = Delta U + W','It expresses conservation of energy','Example: Q=500 J, W=200 J -> Delta U=300 J','State the sign convention first']),
('Thermodynamic processes',['Isothermal -> constant temperature','Isobaric -> constant pressure','Isochoric -> constant volume','Adiabatic -> Q = 0']),
('P-V work',['Area under a quasistatic P-V curve represents work','Expansion increases volume','Compression decreases volume','Use the chosen sign convention consistently']),
('Second law & revision',['Second law gives direction to natural processes','Entropy is a state function linked to thermodynamic direction','Heat engines reject some heat to a sink','Revise system -> law -> process -> sign -> units'])],
'vector':[
('Vector basics',['Vector has magnitude and direction','Scalars have magnitude only','Examples: displacement, velocity, force','A vector can be represented geometrically or by components']),
('Components & unit vectors',['i, j, k are standard Cartesian unit vectors','a = ai + bj + ck','Components simplify vector operations','Magnitude = sqrt(a squared + b squared + c squared)']),
('Addition & subtraction',['Add corresponding components','a - b = a + (-b)','Negative vector has opposite direction','Draw a diagram when direction is confusing']),
('Dot product',['a dot b = |a||b| cos theta','Result is a scalar','a dot b = 0 means non-zero vectors are perpendicular','Use components by multiplying corresponding parts and adding']),
('Cross product',['a cross b is perpendicular to both vectors','Magnitude = |a||b| sin theta','Direction follows the right-hand rule','Its magnitude gives parallelogram area']),
('Line & revision',['Vector line: r = a + lambda b','a gives a point; b gives direction','Keep scalar and vector results distinct','Revise magnitude -> components -> dot -> cross -> line'])],
}
content={k:v for k,v in content.items() if k in {'electricity','thermodynamics','vector'}}
for topic,slides in content.items():
    tmp=out/f'_{topic}_slides'; shutil.rmtree(tmp,ignore_errors=True); tmp.mkdir()
    for i,(title,bullets) in enumerate(slides):
        im=Image.new('RGB',(1280,720),(248,244,236)); d=ImageDraw.Draw(im)
        d.rectangle((0,0,1280,115),fill=(122,16,16)); d.rectangle((0,115,1280,123),fill=(184,134,11))
        d.text((65,32),f'Learn4All  •  {topic.title()}',font=FM,fill=(255,253,248))
        d.text((70,165),f'{i+1}. {title}',font=FB,fill=(122,16,16))
        y=265
        for b in bullets:
            # wrap at ~62 chars
            words=b.split(); lines=[]; cur=''
            for w in words:
                test=(cur+' '+w).strip()
                if len(test)>58:
                    lines.append(cur); cur=w
                else: cur=test
            if cur: lines.append(cur)
            d.ellipse((78,y+8,91,y+21),fill=(184,134,11))
            for line in lines:
                d.text((112,y),line,font=FT,fill=(36,32,28)); y+=44
            y+=18
        d.text((70,650),'Understand • Apply • Check',font=FS,fill=(111,105,97))
        im.save(tmp/f'{i:02}.png')
    listfile=tmp/'concat.txt'
    with listfile.open('w') as f:
        for i in range(len(slides)):
            f.write(f"file '{(tmp/f'{i:02}.png').as_posix()}'\n")
            f.write('duration 10\n')
        f.write(f"file '{(tmp/f'{len(slides)-1:02}.png').as_posix()}'\n")
    dest=out/f'{topic}.mp4'
    cmd=['ffmpeg','-y','-f','concat','-safe','0','-i',str(listfile),'-vf','fps=12,format=yuv420p','-c:v','libx264','-preset','ultrafast','-crf','24','-movflags','+faststart',str(dest)]
    subprocess.run(cmd,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    shutil.rmtree(tmp,ignore_errors=True)
    print(topic,dest.stat().st_size)
