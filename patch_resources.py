from pathlib import Path
p=Path('/mnt/data/work/app.py')
s=p.read_text()
start=s.index('def resource_content(resource):')
end=s.index('@app.route("/resources")', start)
new=r'''def _q(question, options, answer):
    return {"question": question, "options": options, "answer": answer}


RESOURCE_LIBRARY = {
    "fractions": {
        "summary": "Fractions represent parts of a whole. This lesson builds from numerator and denominator to equivalent fractions, comparison, and the four operations.",
        "sections": [
            ("1. Parts of a fraction", "The numerator tells how many equal parts are being considered. The denominator tells how many equal parts make the whole. In 3/5, 3 is the numerator and 5 is the denominator."),
            ("2. Equivalent fractions", "Multiplying or dividing the numerator and denominator by the same non-zero number gives an equivalent fraction. For example, 2/3 = 4/6 = 6/9."),
            ("3. Comparing fractions", "With the same denominator, the larger numerator gives the larger fraction. With different denominators, convert to a common denominator or compare using cross multiplication."),
            ("4. Addition and subtraction", "Fractions with the same denominator can be added directly. With different denominators, first find a common denominator, then add or subtract the numerators."),
            ("5. Multiplication and division", "Multiply numerators and denominators for multiplication. For division, multiply by the reciprocal of the second fraction. Simplify the final answer."),
            ("6. Worked example", "For 1/4 + 2/3, the LCM of 4 and 3 is 12. Convert to 3/12 + 8/12 = 11/12."),
        ],
        "video": ["What a fraction represents", "Equivalent fractions and comparison", "Adding and subtracting", "Multiplying and dividing", "Worked example and recap"],
        "practice": ["Simplify 24/36.", "Add 3/8 + 1/4.", "Subtract 5/6 − 1/3.", "Multiply 2/5 × 15/4.", "Divide 3/4 by 2/3.", "Which is larger: 5/8 or 2/3?", "Write 7/10 as a decimal.", "Find 3/7 of 28.", "Convert 11/4 to a mixed number.", "A class has 24 students and 3/8 are absent. How many are absent?"],
        "answers": ["2/3", "5/8", "1/2", "3/2", "9/8", "2/3", "0.7", "12", "2 3/4", "9 students"],
        "quiz": [
            _q("In 3/7, what is the denominator?", ["3", "7", "10"], 1), _q("Which is equivalent to 2/5?", ["4/10", "4/15", "6/20"], 0),
            _q("1/2 + 1/4 =", ["2/6", "3/4", "1/8"], 1), _q("3/4 − 1/4 =", ["1/2", "2/4", "3/8"], 0),
            _q("2/3 × 3/4 =", ["1/2", "2/7", "5/12"], 0), _q("1/2 ÷ 1/4 =", ["1/8", "2", "4"], 1),
            _q("Which is greater?", ["3/8", "1/2", "2/5"], 1), _q("A common denominator for 1/3 and 1/4 is", ["7", "12", "9"], 1),
            _q("12/18 in simplest form is", ["2/3", "3/2", "6/9"], 0), _q("5/4 as a mixed number is", ["1 1/4", "4 1/5", "1 1/5"], 0),
            _q("3/5 of 20 is", ["8", "12", "15"], 1), _q("0.75 as a fraction is", ["1/4", "3/4", "7/5"], 1),
            _q("If numerator = denominator, the fraction equals", ["0", "1", "2"], 1), _q("2/9 + 4/9 =", ["6/9", "2/18", "8/9"], 0),
            _q("7/10 − 2/10 =", ["5/10", "9/10", "1/2"], 0), _q("The reciprocal of 3/5 is", ["3/5", "5/3", "2/5"], 1),
            _q("Which fraction is less than 1?", ["7/5", "9/8", "4/7"], 2), _q("4/6 simplifies to", ["2/3", "3/2", "1/3"], 0),
            _q("A fraction is in lowest terms when", ["numerator is even", "no common factor greater than 1 remains", "denominator is 10"], 1),
        ],
    },
    "geometry": {
        "summary": "Geometry connects angles, triangles, quadrilaterals, circles, perimeter and area through diagrams and formulas.",
        "sections": [
            ("1. Angle basics", "A right angle is 90°, a straight angle is 180°, and a full turn is 360°. Complementary angles total 90° and supplementary angles total 180°."),
            ("2. Triangles", "The three interior angles of a triangle total 180°. An isosceles triangle has two equal sides and equal opposite angles; an equilateral triangle has three equal sides and three 60° angles."),
            ("3. Quadrilaterals", "The interior angles of a quadrilateral total 360°. Rectangle area is length × breadth, while its perimeter is 2(l+b)."),
            ("4. Circles", "Radius is half the diameter. Circumference = 2πr and area = πr². Keep units consistent before substituting values."),
            ("5. Coordinate thinking", "Distance and shape relationships can be checked using horizontal and vertical changes. Sketching the figure first often prevents formula mistakes."),
            ("6. Worked example", "A triangle has angles 55° and 65°. The third angle is 180° − 55° − 65° = 60°."),
        ],
        "video": ["Reading geometric diagrams", "Angles and triangle rules", "Quadrilaterals and perimeter", "Circle measurements", "Worked problem and recap"],
        "practice": ["Find the third angle of a triangle with 55° and 65°.", "Find the area of an 8 × 5 rectangle.", "Find the perimeter of a 9 × 4 rectangle.", "Find circumference for r = 7 using π = 22/7.", "Find area for r = 7 using π = 22/7.", "Find the missing angle if two supplementary angles are 115° and x.", "What is each angle of an equilateral triangle?", "A square has side 6 cm. Find its area.", "A square has side 6 cm. Find its perimeter.", "State the sum of the interior angles of a quadrilateral."],
        "answers": ["60°", "40 square units", "26 units", "44 units", "154 square units", "65°", "60°", "36 cm²", "24 cm", "360°"],
        "quiz": [
            _q("Angles in a triangle total", ["90°", "180°", "360°"], 1), _q("A right angle measures", ["45°", "90°", "180°"], 1),
            _q("A straight angle measures", ["90°", "180°", "270°"], 1), _q("Complementary angles total", ["90°", "180°", "360°"], 0),
            _q("Supplementary angles total", ["90°", "180°", "270°"], 1), _q("Each angle of an equilateral triangle is", ["45°", "60°", "90°"], 1),
            _q("Interior angles of a quadrilateral total", ["180°", "270°", "360°"], 2), _q("Area of a rectangle is", ["l+b", "2(l+b)", "l×b"], 2),
            _q("Perimeter of a rectangle is", ["l×b", "2(l+b)", "πr²"], 1), _q("Circumference of a circle is", ["2πr", "πr²", "πd²"], 0),
            _q("Area of a circle is", ["2πr", "πr²", "r²/π"], 1), _q("Radius is", ["twice the diameter", "half the diameter", "equal to circumference"], 1),
            _q("A square with side 6 has area", ["12", "24", "36"], 2), _q("A 8×5 rectangle has area", ["13", "40", "26"], 1),
            _q("A 9×4 rectangle has perimeter", ["13", "26", "36"], 1), _q("If two angles are supplementary and one is 115°, the other is", ["65°", "75°", "55°"], 0),
            _q("If two angles are complementary and one is 35°, the other is", ["55°", "65°", "145°"], 0), _q("A full turn is", ["180°", "270°", "360°"], 2),
            _q("The diameter of a circle with radius 7 is", ["3.5", "7", "14"], 2), _q("An isosceles triangle has", ["two equal sides", "three unequal sides", "four sides"], 0),
        ],
    },
    "algebra": {
        "summary": "Algebra uses variables and expressions to represent relationships. The lesson covers like terms, equations, expansion and substitution.",
        "sections": [
            ("1. Variables and constants", "A variable represents an unknown or changing value. A constant has a fixed value. In 5x + 3, x is the variable and 3 is the constant."),
            ("2. Like terms", "Only terms with the same variable part can be combined. 4x + 3x = 7x, but 4x + 3y cannot be simplified into one term."),
            ("3. Solving equations", "Keep both sides balanced. Use inverse operations in reverse order to isolate the variable."),
            ("4. Expansion", "Use the distributive property: a(b+c) = ab + ac. Apply it to every term inside the bracket."),
            ("5. Substitution", "Replace a variable with its known value, then simplify carefully using the correct order of operations."),
            ("6. Worked example", "For 3x + 5 = 20, subtract 5 from both sides to get 3x = 15, then divide by 3: x = 5."),
        ],
        "video": ["Variables and expressions", "Combining like terms", "Solving equations", "Expansion and substitution", "Worked equation"],
        "practice": ["Solve 3x + 5 = 20.", "Simplify 4a + 3a − 2.", "Expand 2(x + 4).", "Solve 5y − 7 = 18.", "Simplify 3p + 2p + 4.", "Find 2x + 3 when x = 4.", "Expand 3(a − 2).", "Solve x/4 = 6.", "Solve 2x − 9 = 13.", "Simplify 7m − 2m + 5."],
        "answers": ["x = 5", "7a − 2", "2x + 8", "y = 5", "5p + 4", "11", "3a − 6", "x = 24", "x = 11", "5m + 5"],
        "quiz": [
            _q("Solve 3x + 5 = 20", ["x=3", "x=5", "x=15"], 1), _q("4a + 3a simplifies to", ["7a", "12a", "a"], 0),
            _q("2(x+4) equals", ["2x+4", "2x+8", "x+8"], 1), _q("A variable is", ["always 0", "an unknown or changing quantity", "a unit"], 1),
            _q("A constant is", ["a fixed value", "always x", "a fraction only"], 0), _q("Like terms have", ["the same variable part", "different variables", "no coefficients"], 0),
            _q("5y−7=18 gives", ["y=5", "y=11", "y=25"], 0), _q("x/4=6 gives", ["x=10", "x=20", "x=24"], 2),
            _q("2x−9=13 gives", ["x=2", "x=11", "x=22"], 1), _q("3(a−2) expands to", ["3a−2", "3a−6", "a−6"], 1),
            _q("If x=4, 2x+3 is", ["8", "11", "12"], 1), _q("7m−2m+5 is", ["5m+5", "9m", "5m−5"], 0),
            _q("The inverse of addition is", ["multiplication", "subtraction", "division"], 1), _q("The inverse of multiplication is", ["division", "addition", "subtraction"], 0),
            _q("3x+2x+4 combines to", ["5x+4", "6x+4", "5x+2"], 0), _q("If x=0, 7x+2 is", ["0", "2", "7"], 1),
            _q("4(x+2) expands to", ["4x+2", "4x+8", "x+8"], 1), _q("x+6=10 gives", ["x=4", "x=6", "x=16"], 0),
            _q("2x=18 gives", ["x=8", "x=9", "x=36"], 1), _q("Substitution means", ["replacing a variable with a value", "removing all variables", "adding variables"], 0),
        ],
    },
    "photosynthesis": {
        "summary": "Photosynthesis explains how green plants use light energy to make glucose from carbon dioxide and water, releasing oxygen.",
        "sections": [
            ("1. What is photosynthesis?", "It is the process by which green plants capture light energy and use it to make glucose from carbon dioxide and water."),
            ("2. Chlorophyll", "Chlorophyll is the green pigment that absorbs light energy. It is found in chloroplasts in plant cells."),
            ("3. Raw materials", "Carbon dioxide enters mainly through stomata. Water is absorbed by roots and transported to leaves through xylem."),
            ("4. Products", "Glucose is produced and can be used for respiration or stored as starch. Oxygen is released as a by-product."),
            ("5. Factors", "Light intensity, carbon dioxide concentration and temperature can affect the rate of photosynthesis within suitable ranges."),
            ("6. Equation", "A simplified word equation is: carbon dioxide + water —light/chlorophyll→ glucose + oxygen."),
        ],
        "video": ["Where photosynthesis happens", "Light and chlorophyll", "Carbon dioxide and water", "Glucose and oxygen", "Factors and recap"],
        "practice": ["Name the pigment that captures light.", "Which gas is used as a raw material?", "Where does most gas exchange occur in leaves?", "Which tissue carries water upward?", "What carbohydrate is first produced?", "What gas is released?", "Where are chloroplasts found?", "Name one factor affecting rate.", "Why is light needed?", "Write the word equation."],
        "answers": ["Chlorophyll", "Carbon dioxide", "Stomata", "Xylem", "Glucose", "Oxygen", "Plant cells", "Light intensity", "It supplies energy", "Carbon dioxide + water → glucose + oxygen"],
        "quiz": [
            _q("Which pigment captures light?", ["Chlorophyll", "Haemoglobin", "Keratin"], 0), _q("Main gas raw material is", ["Oxygen", "Carbon dioxide", "Nitrogen"], 1),
            _q("Water is mainly transported by", ["Xylem", "Phloem", "Stomata"], 0), _q("Gas exchange mainly occurs through", ["Roots", "Stomata", "Seeds"], 1),
            _q("Main carbohydrate produced is", ["Glucose", "Protein", "Fat"], 0), _q("Gas released is", ["Nitrogen", "Oxygen", "Carbon dioxide"], 1),
            _q("Photosynthesis needs", ["Light energy", "Darkness only", "No water"], 0), _q("Chlorophyll is found in", ["Chloroplasts", "Ribosomes", "Nuclei only"], 0),
            _q("Stomata are usually found on", ["Leaves", "Roots only", "Seeds only"], 0), _q("Xylem transports", ["Water and minerals", "Glucose only", "Oxygen only"], 0),
            _q("Phloem mainly transports", ["Sugars/food", "Water only", "Light"], 0), _q("A product of photosynthesis is", ["Glucose", "Urea", "Lactic acid"], 0),
            _q("Increasing suitable light intensity can", ["increase photosynthesis", "always stop it", "remove chlorophyll"], 0), _q("Carbon dioxide enters leaves mainly through", ["Stomata", "Xylem", "Roots"], 0),
            _q("Green leaves appear green mainly because chlorophyll", ["reflects green light", "absorbs all green light", "contains no pigment"], 0), _q("Photosynthesis converts light energy into", ["chemical energy in food", "sound", "mechanical energy only"], 0),
            _q("Stored glucose is commonly converted to", ["Starch", "Salt", "Water"], 0), _q("A suitable temperature is important because", ["enzymes control reactions", "plants need no enzymes", "temperature never matters"], 0),
            _q("The word equation includes", ["carbon dioxide + water", "oxygen + glucose only", "nitrogen + protein"], 0), _q("Photosynthesis occurs mainly in", ["green plant tissues", "red blood cells", "bones"], 0),
        ],
    },
    "grammar": {
        "summary": "Grammar helps you build clear sentences using correct agreement, parts of speech, punctuation and tense.",
        "sections": [
            ("1. Sentence structure", "A complete sentence normally has a subject and a predicate and expresses a complete thought."),
            ("2. Subject–verb agreement", "A singular subject generally takes a singular verb in the present tense: She goes. A plural subject takes the plural form: They go."),
            ("3. Parts of speech", "Nouns name, verbs show action/state, adjectives describe nouns, and adverbs commonly describe verbs, adjectives or other adverbs."),
            ("4. Tense", "Verb tense shows time. Keep the tense consistent unless there is a clear reason to shift time."),
            ("5. Punctuation", "Full stops, commas, question marks and apostrophes help readers understand sentence structure and meaning."),
            ("6. Editing method", "Read the sentence, identify the subject and verb, check tense, then check punctuation and word choice."),
        ],
        "video": ["Building complete sentences", "Subject–verb agreement", "Parts of speech", "Tense and punctuation", "Editing a sentence"],
        "practice": ["Correct: She go to school every day.", "Identify the verb: The students solved the problem.", "Choose: He is / are ready.", "Change to past tense: They play football.", "Add punctuation: Where are you going", "Identify the adjective: The bright lamp shone.", "Choose: The boys runs / run fast.", "Identify the noun: Riya opened the book.", "Change to future: I study tonight.", "Correct: Me and him went home."],
        "answers": ["She goes to school every day.", "solved", "He is ready.", "They played football.", "Where are you going?", "bright", "run", "Riya/book", "I will study tonight.", "He and I went home."],
        "quiz": [
            _q("Choose the correct sentence", ["She goes to school.", "She go to school.", "She going school."], 0), _q("The verb in 'Students solved' is", ["Students", "solved", "the"], 1),
            _q("He ___ ready", ["is", "are", "am"], 0), _q("They ___ football every day", ["plays", "play", "playing"], 1),
            _q("Past tense of 'go' is", ["goed", "went", "gone"], 1), _q("An adjective describes mainly a", ["noun", "verb only", "punctuation mark"], 0),
            _q("An adverb commonly modifies a", ["verb", "full stop", "article only"], 0), _q("A question normally ends with", [".", "?", ","], 1),
            _q("A full stop is used to", ["end a statement", "join every word", "show a question"], 0), _q("Choose the plural verb", ["runs", "run", "running"], 1),
            _q("The noun in 'The dog barked' is", ["dog", "barked", "the"], 0), _q("Future form of 'I study' can be", ["I studied", "I will study", "I studies"], 1),
            _q("Which is correct?", ["He and I went.", "Me and him went.", "Him and me goes."], 0), _q("A comma can", ["separate parts of a sentence", "replace every verb", "end every question"], 0),
            _q("Past tense of 'play' is", ["played", "plays", "playing"], 0), _q("In 'bright lamp', bright is", ["adjective", "verb", "noun"], 0),
            _q("In 'quickly ran', quickly is", ["adverb", "noun", "pronoun"], 0), _q("Subject–verb agreement means", ["subject and verb match in number", "every verb is plural", "every noun is singular"], 0),
            _q("Which needs a question mark?", ["Where are you?", "I am ready.", "She reads."], 0),
        ],
    },
    "electricity": {
        "summary": "Electricity links charge flow, potential difference and resistance. This resource combines formulas, circuit reasoning and numerical practice.",
        "sections": [
            ("1. Current", "Electric current is the rate of flow of electric charge. The SI unit is ampere (A)."),
            ("2. Potential difference", "Potential difference is energy transferred per unit charge. Its SI unit is volt (V)."),
            ("3. Resistance", "Resistance opposes current. Its SI unit is ohm (Ω). For an ohmic conductor under suitable constant conditions, V = IR."),
            ("4. Series circuits", "In a series circuit, the same current passes through components, while the total resistance is the sum of individual resistances."),
            ("5. Parallel circuits", "In parallel, branches share the same potential difference while current divides among branches."),
            ("6. Worked example", "If I = 2 A and R = 5 Ω, Ohm's law gives V = IR = 10 V."),
        ],
        "video": ["Current and charge", "Voltage and resistance", "Ohm's law", "Series and parallel", "Worked numerical"],
        "practice": ["Find V when I=2 A and R=5 Ω.", "Find I when V=12 V and R=4 Ω.", "Find R when V=20 V and I=2 A.", "What is the SI unit of current?", "What is the SI unit of resistance?", "What is the SI unit of potential difference?", "State Ohm's law.", "What happens to current at a junction?", "What is the series resistance of 2 Ω and 3 Ω?", "Why are household appliances connected in parallel?"],
        "answers": ["10 V", "3 A", "10 Ω", "Ampere", "Ohm", "Volt", "V = IR", "It divides among branches according to the circuit", "5 Ω", "Each appliance gets the supply voltage independently"],
        "quiz": [
            _q("SI unit of current", ["Ampere", "Volt", "Ohm"], 0), _q("SI unit of resistance", ["Volt", "Ohm", "Ampere"], 1),
            _q("SI unit of potential difference", ["Ohm", "Volt", "Watt"], 1), _q("Ohm's law is", ["V=IR", "P=VI only", "Q=It only"], 0),
            _q("If I=2 A and R=5 Ω, V=", ["10 V", "2.5 V", "7 V"], 0), _q("If V=12 V and R=4 Ω, I=", ["3 A", "8 A", "48 A"], 0),
            _q("If V=20 V and I=2 A, R=", ["10 Ω", "40 Ω", "18 Ω"], 0), _q("In series, current is", ["same through components", "always zero", "different in every component"], 0),
            _q("In parallel, voltage across branches is", ["the same", "always zero", "always doubled"], 0), _q("Series resistances 2 Ω and 3 Ω total", ["1 Ω", "5 Ω", "6 Ω"], 1),
            _q("Current is rate of flow of", ["charge", "mass", "light"], 0), _q("Potential difference is energy per unit", ["charge", "mass", "time"], 0),
            _q("Resistance opposes", ["current", "mass", "temperature only"], 0), _q("A voltmeter is connected", ["in parallel", "in series only", "nowhere"], 0),
            _q("An ammeter is connected", ["in series", "in parallel only", "across a resistor only"], 0), _q("Household appliances are generally connected in", ["parallel", "series only", "one single loop"], 0),
            _q("Power can be calculated using", ["P=VI", "V=IR only", "R=V/I only"], 0), _q("If resistance increases at constant V, current", ["decreases", "increases", "stays necessarily identical"], 0),
            _q("If current increases at constant R, voltage", ["increases", "decreases", "becomes zero"], 0),
        ],
    },
    "thermodynamics": {
        "summary": "Thermodynamics studies heat, work, temperature and internal energy. The resource connects the first law with common thermodynamic processes and numerical reasoning.",
        "sections": [
            ("1. System and surroundings", "A thermodynamic system is the part being studied. Everything outside it is the surroundings. Energy can cross the boundary as heat or work depending on the system."),
            ("2. Temperature and heat", "Temperature describes the thermal state of a system. Heat is energy transferred because of a temperature difference; it is not the same thing as temperature."),
            ("3. Internal energy", "Internal energy is the microscopic energy associated with the particles of a system. A change in internal energy depends on the energy transferred to or from the system."),
            ("4. First law", "Using the convention that W is work done by the system, the first law is ΔQ = ΔU + ΔW. It expresses conservation of energy."),
            ("5. Processes", "Isothermal means constant temperature, isobaric means constant pressure, isochoric means constant volume, and adiabatic means no heat transfer into or out of the system."),
            ("6. Work and graphs", "For a quasistatic process, work can be represented by the area under a P–V curve. Expansion generally corresponds to positive work done by the system under the stated convention."),
            ("7. Worked example", "If 500 J of heat enters a system and the system does 200 J of work, then ΔU = 500 − 200 = 300 J using ΔQ = ΔU + ΔW."),
        ],
        "video": ["System, surroundings and heat", "Internal energy", "First law of thermodynamics", "Four common processes", "P–V work and worked example"],
        "practice": ["State the first law using W as work done by the system.", "What remains constant in an isothermal process?", "Name the constant-volume process.", "Name the constant-pressure process.", "What is true of heat transfer in an adiabatic process?", "If Q=500 J and W=200 J, find ΔU.", "What does the area under a P–V curve represent?", "Differentiate heat and temperature.", "What is internal energy?", "A gas expands while doing 150 J work and receives 400 J heat. Find ΔU."],
        "answers": ["ΔQ = ΔU + ΔW", "Temperature", "Isochoric", "Isobaric", "No heat transfer", "300 J", "Work done", "Heat is energy transfer; temperature measures thermal state", "Microscopic energy of the system", "250 J"],
        "quiz": [
            _q("The first law expresses conservation of", ["Energy", "Charge", "Mass only"], 0), _q("With W as work done by system, first law is", ["ΔQ=ΔU+ΔW", "ΔQ=ΔU−ΔW always", "ΔU=0 always"], 0),
            _q("Isothermal means constant", ["Temperature", "Pressure", "Volume"], 0), _q("Isobaric means constant", ["Temperature", "Pressure", "Volume"], 1),
            _q("Isochoric means constant", ["Temperature", "Pressure", "Volume"], 2), _q("Adiabatic means", ["no heat transfer", "constant temperature", "constant pressure"], 0),
            _q("Heat is", ["energy transferred due to temperature difference", "the same as temperature", "a substance"], 0), _q("Temperature describes", ["thermal state", "only volume", "only mass"], 0),
            _q("If Q=500 J and W=200 J, ΔU=", ["300 J", "700 J", "200 J"], 0), _q("If Q=400 J and W=150 J, ΔU=", ["250 J", "550 J", "150 J"], 0),
            _q("The area under a P–V curve represents", ["work", "temperature directly", "mass"], 0), _q("Internal energy is associated with", ["microscopic energy", "only gravitational energy", "only external work"], 0),
            _q("A constant-volume process is", ["isochoric", "isothermal", "isobaric"], 0), _q("A constant-pressure process is", ["isobaric", "adiabatic", "isochoric"], 0),
            _q("An isothermal process keeps", ["T constant", "P constant", "V constant"], 0), _q("In an adiabatic process, Q is", ["0", "always 100 J", "always equal to W"], 0),
            _q("If a system receives heat, Q is positive under the common convention", ["True", "False", "Only at 0°C"], 0), _q("If system does work while receiving heat, some heat can", ["increase internal energy and some can become work", "vanish", "turn into mass automatically"], 0),
            _q("Thermodynamics studies relationships among", ["heat, work, temperature and energy", "only speed", "only electricity"], 0),
        ],
    },
}


def _generic_resource(topic, subject):
    """Generate a useful fallback structure for a newly entered topic."""
    return {
        "summary": f"A guided learning pack for {topic} in {subject}, designed to move from definitions to examples, practice and self-checking.",
        "sections": [
            ("1. Start with the idea", f"Write a one-sentence definition of {topic}. Identify what the topic describes, measures or helps you calculate."),
            ("2. Core vocabulary", f"List the important terms used in {topic}. For each term, write its meaning and one simple example."),
            ("3. Method", f"Break a typical {topic} problem into: identify the data, choose the relevant rule or formula, substitute carefully, and check units."),
            ("4. Worked example", f"Take one representative {topic} question. Highlight the known values, the required quantity and each step leading to the result."),
            ("5. Common mistakes", "Watch for unit mismatches, copied signs, skipped steps and answers that do not match the question asked."),
            ("6. Self-check", "Explain the concept without looking at the notes, then solve a fresh question to confirm that you can transfer the idea."),
        ],
        "video": [f"What is {topic}?", "Key vocabulary", "Worked example", "Common mistakes", "Self-check and recap"],
        "practice": [f"Define {topic} in your own words.", f"List three key terms from {topic}.", f"State one important rule or formula used in {topic}.", f"Solve one standard {topic} example from your notes.", f"Explain one common mistake in {topic}.", f"Write one real-world application of {topic}.", f"Create a one-line summary of {topic}.", f"Write one question you still have about {topic}.", f"Check the units in a typical {topic} calculation.", f"Explain {topic} to a classmate in three steps."],
        "answers": ["Use your textbook definition.", "Use the key vocabulary from the lesson.", "Use the relevant rule or formula.", "Show all calculation steps.", "Check units, signs and assumptions.", "Give a relevant application.", "Capture the central idea.", "Write a specific concept question.", "Make every unit consistent.", "Use definition → method → example."],
        "quiz": [_q(f"Which is the best first step when studying {topic}?", ["Identify the concept", "Skip the definition", "Guess the answer"], 0) for _ in range(20)],
    }


def resource_content(resource):
    """Return detailed, topic-aware content for video, notes, quiz and practice resources."""
    topic = str(resource["topic"]).strip()
    data = RESOURCE_LIBRARY.get(topic.casefold(), _generic_resource(topic, resource["subject"]))
    return data


'''
p.write_text(s[:start]+new+s[end:])
